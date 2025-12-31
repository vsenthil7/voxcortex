from services.shared.config import settings
from services.voiceio.prosody_encoder import prosody_from_confidence
import urllib.request
import json

def tts(text: str, confidence: float) -> bytes:
    # Phase 0 stub if key missing
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        return f"STUB-AUDIO: {text}".encode("utf-8")

    prosody = prosody_from_confidence(confidence)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": prosody["stability"],
            "similarity_boost": 0.85,
            "style": prosody["style"],
            "use_speaker_boost": True
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": settings.elevenlabs_api_key,
            "Accept": "audio/mpeg"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()
