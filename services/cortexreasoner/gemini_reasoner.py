# services/cortexreasoner/gemini_reasoner.py

import os
import json
import re

from google import genai
from google.genai import types

MODEL_PRIMARY = os.getenv(
    "GEMINI_REASONER_MODEL",
    "models/gemini-2.5-pro"
)

_client = genai.Client(
    api_key=os.environ["GOOGLE_API_KEY"]
)

def explain(belief: dict, evidence: list[dict]) -> dict:
    """
    Produce a bounded, evidence-grounded explanation.
    STRICT JSON only.
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

    response = _client.models.generate_content(
        model=MODEL_PRIMARY,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
        ]
    )


    text = response.text.strip()
    
    # Strip fenced code blocks: ```json ... ```
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    
    # Extract first JSON object if extra text exists
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise RuntimeError(f"No JSON object found in Gemini output:\n{text}")
        text = match.group(0)
    
    try:
        return json.loads(text)
    except Exception as e:
        raise RuntimeError(
            f"Gemini returned unparseable JSON:\n{text}"
        ) from e
