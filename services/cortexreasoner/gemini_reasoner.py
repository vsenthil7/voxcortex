# services/cortexreasoner/gemini_reasoner.py

import os
import json
import re
from google import genai
from google.genai import types
from google.genai.errors import ClientError

MODEL_PRIMARY = os.getenv(
    "GEMINI_REASONER_MODEL",
    "models/gemini-2.5-flash"
)

_client = genai.Client(
    api_key=os.environ.get("GOOGLE_API_KEY")
)


def _safe_json_parse(text: str) -> dict:
    """
    Hardened JSON parser:
    - strips markdown fences
    - extracts first JSON object only
    - fails loudly if invalid
    """
    if not text:
        raise ValueError("Empty response from Gemini")

    # Remove ```json fences if present
    text = re.sub(r"```json|```", "", text).strip()

    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end <= start:
        raise ValueError(f"No JSON object found in:\n{text}")

    return json.loads(text[start:end])


def explain(belief: dict, evidence: list[dict]) -> dict:
    """
    Produce a bounded, evidence-grounded explanation.
    STRICT JSON only.
    NEVER breaks the pipeline.
    """

    prompt = f"""
You are VoxCortex, an incident reasoning engine.

Rules:
- Use ONLY provided evidence IDs
- Do NOT invent facts
- Express uncertainty when confidence < 0.9
- Return STRICT JSON only with keys:
  - explanation
  - confidence_language {{ tone, markers[] }}
  - evidence_ids[]
  - why_not[]
  - what_would_change_my_mind[]

Belief:
{json.dumps(belief, indent=2)}

Evidence:
{json.dumps(evidence, indent=2)}
""".strip()

    try:
        response = _client.models.generate_content(
            model=MODEL_PRIMARY,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt)]
                )
            ],
        )
        return _safe_json_parse(response.text)

    except ClientError as e:
        # RATE LIMIT / QUOTA SAFE DEGRADE
        if getattr(e, "status_code", None) == 429:
            return {
                "explanation": "Explanation deferred due to Gemini rate limits.",
                "confidence_language": {
                    "tone": "unknown",
                    "markers": ["rate_limited", "deferred"]
                },
                "evidence_ids": [],
                "why_not": ["Gemini API quota exhausted"],
                "what_would_change_my_mind": [
                    "Retry after Gemini quota reset"
                ],
            }
        raise

    except Exception as e:
        raise RuntimeError(
            f"Gemini returned invalid output:\n{str(e)}"
        ) from e
