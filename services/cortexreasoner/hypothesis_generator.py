import os
import json
import logging
from typing import Any, Dict

from google import genai
from services.policy.policy_gate import PolicyGate, PolicyViolation

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

MODEL_PRIMARY = os.getenv(
    "GEMINI_REASONER_MODEL",
    "models/gemini-2.5-flash",
)

_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

# -------------------------------------------------------------------
# explain()
#
# Phase-1 ENABLED
# - AI reasoning allowed
# - NO actions
# - NO tools
# - PolicyGate enforced
#
# Backward compatible:
#   explain(belief, evidence)                 # Phase-0 caller
#   explain(trace_id, belief, evidence)       # Phase-1+
#   explain(trace_id=..., belief=..., evidence=...)
# -------------------------------------------------------------------

def explain(*args, **kwargs) -> Dict[str, Any]:
    trace_id = None
    belief = None
    evidence = None

    # -------- Argument normalization --------
    if len(args) == 2:
        belief, evidence = args
        trace_id = kwargs.get("trace_id", "phase0")
    elif len(args) == 3:
        trace_id, belief, evidence = args
    elif len(args) == 0:
        trace_id = kwargs.get("trace_id", "kw")
        belief = kwargs.get("belief")
        evidence = kwargs.get("evidence")
    else:
        raise TypeError(
            "explain() supports (belief, evidence), "
            "(trace_id, belief, evidence), or keyword arguments"
        )

    if belief is None or evidence is None:
        raise TypeError("explain() missing required belief and evidence")

    # ----------------------------------------------------------------
    # Phase-1 reasoning prompt (STRICT)
    # ----------------------------------------------------------------

    prompt = f"""
You are a reasoning component inside an enterprise system.

ABSOLUTE RULES:
- NO actions
- NO tools
- NO database operations
- OUTPUT VALID JSON ONLY
- DO NOT include markdown
- DO NOT include commentary

Required JSON schema:
{{
  "explanation": "...",
  "confidence_language": {{ "...": "..." }},
  "evidence_ids": ["..."],
  "what_would_change_my_mind": ["..."]
}}

Context:
belief = {json.dumps(belief, ensure_ascii=False)}
evidence = {json.dumps(evidence, ensure_ascii=False)}
trace_id = "{trace_id}"

Return ONLY the JSON object.
""".strip()

    response = _client.models.generate_content(
        model=MODEL_PRIMARY,
        contents=prompt,
    )

    raw_text = getattr(response, "text", None) or str(response)
    raw_text = raw_text.strip()

    # ----------------------------------------------------------------
    # HARD JSON EXTRACTION (NO TRUST)
    # ----------------------------------------------------------------

    start = raw_text.find("{")
    end = raw_text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise PolicyViolation(
            f"No valid JSON object found in Gemini output (trace={trace_id})"
        )

    json_text = raw_text[start:end + 1]

    # ----------------------------------------------------------------
    # PolicyGate enforcement
    # ----------------------------------------------------------------

    try:
        validated = PolicyGate.validate(json_text)
        logger.info(
            "PolicyGate accepted Gemini output (trace=%s)", trace_id
        )
        return validated

    except PolicyViolation as e:
        logger.warning(
            "PolicyGate REJECTED Gemini output (trace=%s): %s",
            trace_id,
            e,
        )

    # ----------------------------------------------------------------
    # SAFE FAIL (SYSTEM CONTINUES, NO ACTIONS)
    # ----------------------------------------------------------------

    return {
        "explanation": (
            "Gemini output violated Phase-1 policy and was rejected. "
            "This explanation is system-generated and non-actionable."
        ),
        "confidence_language": {
            "level": "unknown",
            "calibration": "blocked_by_policy_gate",
        },
        "evidence_ids": [],
        "what_would_change_my_mind": [
            "Provide a valid JSON-only response that cites evidence_ids "
            "and follows Phase-1 policy constraints."
        ],
    }
