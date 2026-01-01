# services/cortexreasoner/gemini_reasoner.py
import os
import json
import logging
from typing import Any, Dict, Optional, Tuple

from google import genai

from services.policy.policy_gate import PolicyGate, PolicyViolation
from services.audit.ai_call_audit import record_ai_call

logger = logging.getLogger(__name__)

MODEL_PRIMARY = os.getenv("GEMINI_REASONER_MODEL", "models/gemini-2.5-flash")
_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def _normalize_inputs(*args, **kwargs) -> Tuple[str, Optional[str], Any, Any]:
    """
    VALID signatures (ALL supported):
      explain(belief, evidence)
      explain(trace_id, belief, evidence)
      explain(trace_id, belief=..., evidence=..., belief_id=...)
      explain(trace_id=..., belief=..., evidence=..., belief_id=...)
    """

    belief = None
    evidence = None

    # --- trace_id ---
    if len(args) >= 1 and isinstance(args[0], str):
        trace_id = args[0]
    else:
        trace_id = kwargs.get("trace_id", "phase0")

    belief_id = kwargs.get("belief_id")

    # --- belief / evidence ---
    if len(args) == 3:
        _, belief, evidence = args
    elif len(args) == 2:
        belief, evidence = args
    else:
        belief = kwargs.get("belief")
        evidence = kwargs.get("evidence")

    if belief is None or evidence is None:
        raise TypeError("belief and evidence are required")

    return str(trace_id), belief_id, belief, evidence


def explain(*args, **kwargs) -> Dict[str, Any]:
    trace_id, belief_id, belief, evidence = _normalize_inputs(*args, **kwargs)

    prompt = f"""
You are a reasoning component.

RULES:
- NO actions
- NO tools
- NO DB instructions
- JSON ONLY (no markdown)

Required JSON:
{{
  "explanation": "...",
  "confidence_language": {{ "level": "...", "calibration": "..." }},
  "evidence_ids": ["..."],
  "what_would_change_my_mind": ["..."]
}}

Context:
belief = {json.dumps(belief, default=str)}
evidence = {json.dumps(evidence, default=str)}
belief_id = "{belief_id}"
trace_id = "{trace_id}"

Return ONLY JSON.
""".strip()

    response = _client.models.generate_content(
        model=MODEL_PRIMARY,
        contents=prompt,
    )

    raw_text = getattr(response, "text", None) or str(response)

    parsed_json = None
    policy_status = "REJECTED"
    policy_error = None

    try:
        parsed_json = PolicyGate.validate(raw_text)
        policy_status = "ACCEPTED"
    except PolicyViolation as e:
        policy_error = str(e)

    # --- ALWAYS audit ---
    try:
        record_ai_call(
            trace_id=trace_id,
            phase="phase1",
            model_name=MODEL_PRIMARY,
            prompt=prompt,
            raw_output=raw_text,
            parsed_json=parsed_json,
            policy_status=policy_status,
            policy_error=policy_error,
        )
    except Exception:
        logger.exception("AI audit write failed but continuing")

    if policy_status == "ACCEPTED":
        return parsed_json

    return {
        "explanation": "Model output rejected by policy",
        "confidence_language": {"level": "unknown", "calibration": "blocked"},
        "evidence_ids": [],
        "what_would_change_my_mind": ["Return valid Phase-1 JSON"],
    }
