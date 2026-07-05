# Azure Speech REST API — TTS Quick Reference

> For MELISSA-TTS. REST alternative when SDK is not available.

## Endpoint

```
POST https://{region}.tts.speech.microsoft.com/cognitiveservices/v1
```

## Auth

```
Header: Ocp-Apim-Subscription-Key: {key}
```

## Request

```http
POST /cognitiveservices/v1 HTTP/1.1
Host: {region}.tts.speech.microsoft.com
Content-Type: application/ssml+xml
X-Microsoft-OutputFormat: audio-16khz-32kbitrate-mono-mp3
Ocp-Apim-Subscription-Key: {key}

<speak version='1.0' xml:lang='es-MX'>
  <voice name='es-MX-DaliaNeural'>Hola Arturo</voice>
</speak>
```

## Output Formats

| Value                              | Description           |
|------------------------------------|-----------------------|
| audio-16khz-32kbitrate-mono-mp3    | MP3 16kHz (default)   |
| audio-24khz-48kbitrate-mono-mp3    | MP3 24kHz HQ          |
| audio-16khz-16bit-mono-pcm         | WAV 16kHz             |
| audio-24khz-16bit-mono-pcm         | WAV 24kHz             |
| raw-16khz-16bit-mono-pcm           | Raw PCM               |
| riff-16khz-16bit-mono-pcm          | RIFF WAV              |

## Python Example (requests)

```python
import requests

def tts_rest(text: str, voice: str = "es-MX-DaliaNeural", region: str = "eastus"):
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"],
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
    }
    ssml = f"<speak version='1.0' xml:lang='es-MX'><voice name='{voice}'>{text}</voice></speak>"
    response = requests.post(url, headers=headers, data=ssml.encode("utf-8"))
    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            f.write(response.content)
        return "output.mp3"
    raise RuntimeError(f"TTS REST failed: {response.status_code} {response.text}")
```

## Long Audio API (Async, >10 min)

For documents longer than 10 minutes, use the batch synthesis API:

```
PUT https://{region}.customvoice.api.speech.microsoft.com/api/texttospeech/v3.1/longaudiosynthesis/{id}
```

## cURL Quick Test

```bash
curl -X POST "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1" \
  -H "Ocp-Apim-Subscription-Key: $AZURE_SPEECH_KEY" \
  -H "Content-Type: application/ssml+xml" \
  -H "X-Microsoft-OutputFormat: audio-16khz-32kbitrate-mono-mp3" \
  -d "<speak version='1.0' xml:lang='es-MX'><voice name='es-MX-DaliaNeural'>Hola Arturo</voice></speak>" \
  --output output.mp3
```