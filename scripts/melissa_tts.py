#!/usr/bin/env python3
"""MELISSA-TTS: Text-to-Speech multilingue (zh/ES/EN/JP)

Uso:
  python melissa_tts.py "Hola Arturo" --lang es-MX --output salida.mp3
  python melissa_tts.py "你好世界" --lang zh-CN
  python melissa_tts.py "Hello" --lang en-US --method edge
  echo "Texto" | python melissa_tts.py --lang ja-JP

Prioridad: Azure Speech Service > Edge-TTS (fallback)
"""

import argparse
import asyncio
import os
import re
import sys


VOICES = {
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "es-MX": "es-MX-DaliaNeural",
    "en-US": "en-US-JennyNeural",
    "ja-JP": "ja-JP-NanamiNeural",
}

LANG_TAGS = {
    "zh-CN": "zh-CN",
    "es-MX": "es-MX",
    "en-US": "en-US",
    "ja-JP": "ja-JP",
}


def detect_lang(text: str) -> str:
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
    has_hiragana = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    has_es = bool(re.search(r'[áéíóúñ¿¡]', text, re.IGNORECASE))
    if has_hiragana:
        return "ja-JP"
    if has_cjk:
        return "zh-CN"
    if has_es:
        return "es-MX"
    return "en-US"


def synthesize_azure(text: str, lang: str, output: str) -> str:
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("[MELISSA-TTS] azure-cognitiveservices-speech no instalado. Usando Edge-TTS.", file=sys.stderr)
        return asyncio.run(synthesize_edge(text, lang, output))

    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION", "eastus")
    if not key:
        print("[MELISSA-TTS] AZURE_SPEECH_KEY no configurado. Usando Edge-TTS.", file=sys.stderr)
        return asyncio.run(synthesize_edge(text, lang, output))

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = VOICES.get(lang, "es-MX-DaliaNeural")
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"[MELISSA-TTS] Audio generado: {output}", file=sys.stderr)
        return output
    elif result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(f"[MELISSA-TTS] Azure cancelado: {details.reason} - {details.error_details}", file=sys.stderr)
        print("[MELISSA-TTS] Fallback a Edge-TTS.", file=sys.stderr)
        return asyncio.run(synthesize_edge(text, lang, output))
    return output


async def synthesize_edge(text: str, lang: str, output: str) -> str:
    try:
        import edge_tts
    except ImportError:
        print("[MELISSA-TTS] edge-tts no instalado. Instala con: pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    voice = VOICES.get(lang, "es-MX-DaliaNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)
    print(f"[MELISSA-TTS] Audio generado (Edge-TTS): {output}", file=sys.stderr)
    return output


def build_ssml(sections: dict, default_lang: str = "es-MX") -> str:
    voices = []
    for lang, text in sections.items():
        voice_name = VOICES.get(lang, VOICES[default_lang])
        lang_tag = LANG_TAGS.get(lang, default_lang)
        voices.append(f'<voice name="{voice_name}" xml:lang="{lang_tag}">{text}</voice>')
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{default_lang}">'
        + "".join(voices) + "</speak>"
    )


def synthesize_azure_ssml(ssml: str, output: str) -> str:
    import azure.cognitiveservices.speech as speechsdk

    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION", "eastus")
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"[MELISSA-TTS] SSML audio generado: {output}", file=sys.stderr)
        return output
    elif result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RuntimeError(f"SSML TTS cancelado: {details.reason} {details.error_details}")
    return output


def main():
    parser = argparse.ArgumentParser(description="MELISSA-TTS: Text-to-Speech multilingue")
    parser.add_argument("text", nargs="?", help="Texto a sintetizar (o usar stdin)")
    parser.add_argument("--lang", default=None, help="Idioma: zh-CN, es-MX, en-US, ja-JP (auto-detect)")
    parser.add_argument("--output", "-o", default="melissa_output.mp3", help="Archivo de salida")
    parser.add_argument("--method", choices=["azure", "edge", "auto"], default="auto", help="Metodo TTS")
    parser.add_argument("--ssml", action="store_true", help="Usar modo SSML multilingue")
    parser.add_argument("--ssml-sections", nargs="*", help="Pares lang=texto para SSML (ej: es-MX=Hola zh-CN=你好)")

    args = parser.parse_args()

    if not args.text:
        if not sys.stdin.isatty():
            args.text = sys.stdin.read().strip()
        else:
            parser.print_help()
            sys.exit(1)

    lang = args.lang or detect_lang(args.text)

    if args.ssml and args.ssmL_sections:
        sections = {}
        for pair in args.ssml_sections:
            l, t = pair.split("=", 1)
            sections[l] = t
        ssml = build_ssml(sections)
        synthesize_azure_ssml(ssml, args.output)
        return

    if args.method == "edge":
        asyncio.run(synthesize_edge(args.text, lang, args.output))
    elif args.method == "azure":
        synthesize_azure(args.text, lang, args.output)
    else:
        synthesize_azure(args.text, lang, args.output)


if __name__ == "__main__":
    main()