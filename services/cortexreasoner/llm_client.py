from services.shared.config import settings
import json
import urllib.request

class GeminiClient:
    """
    Single gateway to Gemini (Phase 0 minimal).
    In prod: add retries, model pinning, structured output validation, and request/response logging.
    """
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    def generate_json(self, prompt: str) -> dict:
        # Phase 0: if no key, deterministic stub output (keeps pipeline testable)
        if not self.api_key:
            return {
                "explanation": "STUB: Gemini API key not configured. Returning deterministic explanation.",
                "confidence_language": {"tone": "uncertain", "markers": ["stub_mode"]},
                "evidence_ids": [],
                "what_would_change_my_mind": ["Configure GEMINI_API_KEY and replay incident."],
            }

        # NOTE: Endpoint specifics may differ based on Gemini API surface you enable.
        # Keep it minimal here; wire the correct endpoint in your build environment.
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
