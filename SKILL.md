---
name: melissa-tts
description: "Convierte salida de texto MELISSA a voz multilingue (中文/ES/EN/JP) usando Azure Speech Service o Edge-TTS como fallback. WHEN: text to speech, TTS, hablar, voz, audio output, sintetizar voz, convertir texto a audio, MELISSA voice, multilingual TTS."
license: MIT
metadata:
  author: IArtLabs
  version: "1.0.0"
  agent: MELISSA
  idiomas: ["zh-CN", "es-MX", "en-US", "ja-JP"]
---

# MELISSA-TTS: Puente Bilingue con Voz

Convierte texto MELISSA a audio multilingue. Prioritario: Azure Speech Service. Fallback: Edge-TTS (gratuito).

## Idiomas Soportados

| Codigo | Idioma | Voz Azure (Neural) | Voz Edge-TTS |
|--------|--------|-------------------|--------------|
| zh-CN | Chino Mandarin | zh-CN-XiaoxiaoNeural | zh-CN-XiaoxiaoNeural |
| es-MX | Espanol Mexico | es-MX-DaliaNeural | es-MX-DaliaNeural |
| en-US | Ingles EE.UU. | en-US-JennyNeural | en-US-JennyNeural |
| ja-JP | Japones | ja-JP-NanamiNeural | ja-JP-NanamiNeural |

## Metodo 1: Azure Speech Service (Recomendado)

### Prerrequisitos

```bash
pip install azure-cognitiveservices-speech
```

### Variables de Entorno

```
AZURE_SPEECH_KEY=<tu-key>
AZURE_SPEECH_REGION=<tu-region>
```

### Uso via Python SDK

```python
import azure.cognitiveservices.speech as speechsdk

def melissa_speak(text: str, lang: str = "es-MX", output_file: str = "output.wav"):
    voices = {
        "zh-CN": "zh-CN-XiaoxiaoNeural",
        "es-MX": "es-MX-DaliaNeural",
        "en-US": "en-US-JennyNeural",
        "ja-JP": "ja-JP-NanamiNeural",
    }
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
    speech_config.speech_synthesis_voice_name = voices.get(lang, "es-MX-DaliaNeural")
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return output_file
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        raise RuntimeError(f"TTS cancelado: {cancellation.reason} - {cancellation.error_details}")
```

### Uso via MCP (Azure MCP habilitado)

```
azure__speech con comando speech_synthesize
Parametros: text, voice, output_format
```

### SSML Multilingue

Para mezclar idiomas en una sola salida:

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-MX">
  <voice name="es-MX-DaliaNeural">
    Hola Arturo, la traduccion es:
    <voice name="zh-CN-XiaoxiaoNeural">
      你好，世界
    </voice>
  </voice>
</speak>
```

### Uso con SSML en Python

```python
def melissa_speak_ssml(ssml: str, output_file: str = "output.wav"):
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return output_file
```

## Metodo 2: Edge-TTS (Fallback Gratuito)

### Instalacion

```bash
pip install edge-tts
```

### Uso

```bash
edge-tts --text "Hola Arturo, soy MELISSA" --voice es-MX-DaliaNeural --write-media output.mp3
```

### Uso via Python

```python
import asyncio
import edge_tts

async def melissa_speak_edge(text: str, lang: str = "es-MX", output_file: str = "output.mp3"):
    voices = {
        "zh-CN": "zh-CN-XiaoxiaoNeural",
        "es-MX": "es-MX-DaliaNeural",
        "en-US": "en-US-JennyNeural",
        "ja-JP": "ja-JP-NanamiNeural",
    }
    voice = voices.get(lang, "es-MX-DaliaNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file
```

## Metodo 3: Script Rapido

Ver `scripts/melissa_tts.py` para script CLI integrado con deteccion automatica de idioma y fallback Edge-TTS.

## Flujo de Decision

```
Texto MELISSA (trilineal)
    |
    v
Detectar idioma predominante (zh/ES/EN/JP)
    |
    v
Azure Speech disponible? --> SI --> Azure TTS (neural, SSML multilingue)
    |
    NO
    v
Edge-TTS (gratuito, sin API key, calidad decente)
```

## Integracion con Formato Trilineal

MELISSA produce formato trilineal. Para TTS, extraer texto plano manteniendo estructura:

```
Entrada MELISSA:
BASE: Perfil cargado
CENTRO: Comunicacion adaptada
ACCION: Esperando GO
VEREDICTO: ACTIVA

Salida TTS (SSML mezclado):
"Hola, BASE, perfil cargado. CENTRO, comunicacion adaptada. ACCION, esperando GO. VEREDICTO, ACTIVA."
```

## Best Practices

1. **SSML para multilingue**: Si el texto mezcla idiomas, usar SSML con etiquetas `<voice>` por idioma
2. **Azure primero**: Siempre intentar Azure Speech antes de Edge-TTS (mejor calidad)
3. **Audio formato**: MP3 para velocidad, WAV si se necesita post-procesar
4. **Cache por voz**: Guardar archivos de voz generados para reutilizar frases comunes
5. **Limite de texto**: Azure Speech soporta hasta 10 minutos por solicitud; para textos largos, dividir en parrafos
6. **Region**: Usar la region mas cercana al usuario para baja latencia

## Limitaciones

- Edge-TTS no soporta SSML multilingue (solo un idioma por solicitud)
- Edge-TTS requiere conexion a internet (no offline)
- Azure Speech requiere subscription key y region
- Japonés (ja-JP) requiere voz Neural especifica (no todas las regions la tienen)

## Referencias SDK

- Azure Speech Python: `references/sdk/azure-speech-py.md`
- Azure Speech REST API: `references/sdk/azure-speech-rest.md`