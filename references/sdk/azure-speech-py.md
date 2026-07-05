# Azure Speech SDK — TTS Python Quick Reference

> Condensed for MELISSA-TTS. Covers Speech Synthesis (TTS) only.

## Install

```bash
pip install azure-cognitiveservices-speech
```

## Auth

```python
import os
import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(
    subscription=os.environ["AZURE_SPEECH_KEY"],
    region=os.environ["AZURE_SPEECH_REGION"],
)
```

## MELISSA Voice Map

| Lang    | Voice Neural             | Gender |
|---------|--------------------------|--------|
| zh-CN   | zh-CN-XiaoxiaoNeural    | F      |
| es-MX   | es-MX-DaliaNeural       | F      |
| en-US   | en-US-JennyNeural       | F      |
| ja-JP   | ja-JP-NanamiNeural      | F      |

## Patterns

### Basic TTS

```python
def synthesize(text: str, voice: str = "es-MX-DaliaNeural", output: str = "out.mp3"):
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return output
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RuntimeError(f"TTS canceled: {details.reason} {details.error_details}")
```

### SSML Multilingual (MELISSA Core)

```python
def synthesize_ssml(ssml: str, output: str = "out.mp3"):
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return output
```

### Stream to Memory (No File)

```python
synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config, audio_config=None
)
result = synthesizer.speak_text_async(text).get()
audio_data = result.audio_data  # bytes
```

### Word Boundary Events

```python
def on_word_boundary(evt):
    print(f"Word: {evt.text} | Offset: {evt.audio_offset} | Duration: {evt.audio_duration}")

synthesizer.synthesis_word_boundary_event.connect(on_word_boundary)
```

### Viseme Events (Lip Sync)

```python
def on_viseme(evt):
    print(f"Viseme {evt.viseme_id} at offset {evt.audio_offset}")

synthesizer.viseme_event.connect(on_viseme)
```

## Output Formats

| Format                                           | Ext  | Use Case          |
|--------------------------------------------------|------|-------------------|
| Audio16Khz32KBitRateMonoMp3                      | .mp3 | General use       |
| Audio24Khz48KBitRateMonoMp3                      | .mp3 | High quality      |
| Audio16Khz16BitMonoPcm                           | .wav | Post-processing   |
| Audio24Khz16BitMonoPcm                            | .wav | High quality wav  |
| Riff16Khz16BitMonoPcm                             | .wav | Compatibility     |

## REST API (Alternative)

```
POST https://{region}.tts.speech.microsoft.com/cognitiveservices/v1
Headers:
  X-Microsoft-OutputFormat: audio-16khz-32kbitrate-mono-mp3
  Content-Type: application/ssml+xml
  Ocp-Apim-Subscription-Key: {key}
Body: <speak version='1.0' xml:lang='es-MX'><voice name='es-MX-DaliaNeural'>Hola</voice></speak>
```

## Error Handling

| Code  | Meaning                | Action                    |
|-------|------------------------|---------------------------|
| 401   | Unauthorized           | Check key/region          |
| 403   | Forbidden              | Check quota/region access |
| 429   | Too Many Requests      | Retry with backoff         |
| 502   | Bad Gateway            | Check region endpoint      |

## Non-Obvious Patterns

- DefaultAzureCredential NOT supported; use subscription key directly
- For long texts (>10 min), split into paragraphs and synthesize each
- SSML `<voice>` tags allow mixing languages in one request
- Set `speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_TranslateToText, value=lang)` for translate-to-speech flows
- Stream results via `audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)` for real-time playback