# services/cortexreasoner/gemini_reasoner.py
import os
import json
import logging
from typing import Any, Dict, Optional, Tuple

from google import genai

from services.policy.policy_gate import PolicyGate, PolicyViolation
from services.audit.ai_call_audit import record_ai_call
from services.cortexreasoner.hypothesis_store import persist_hypotheses

logger = logging.getLogger(__name__)

MODEL_PRIMARY = os.getenv("GEMINI_REASONER_MODEL", "models/gemini-2.5-flash")
_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def _normalize_inputs(*args, **kwargs) -> Tuple[str, Any, Any]:
    """
    Backward-compatible:
      explain(belief, evidence)                 # Phase-0 call sites
      explain(trace_id, belief, evidence)       # Phase-1+
      explain(trace_id=..., belief=..., evidence=...)
    """
    trace_id: Optional[str] = None
    belief = None
    evidence = None

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
            "explain() supports (belief, evidence) OR (trace_id, belief, evidence) OR keyword arguments"
        )

    if belief is None or evidence is None:
        raise TypeError("explain() missing required belief and evidence")

    return str(trace_id), belief, evidence


def _best_effort_belief_id(belief: Any, trace_id: str) -> str:
    if isinstance(belief, dict):
        v = belief.get("belief_id") or belief.get("id") or belief.get("beliefId")
        if v is not None:
            return str(v)
    # fallback still gives you linkage
    return f"unknown:{trace_id}"


def explain(*args, **kwargs) -> Dict[str, Any]:
    trace_id, belief, evidence = _normalize_inputs(*args, **kwargs)

    prompt = f"""
You are a reasoning component inside an enterprise system.

ABSOLUTE RULES (Phase-1):
- NO actions
- NO tools
- NO database instructions
- OUTPUT VALID JSON ONLY
- DO NOT include markdown fences
- DO NOT include commentary outside JSON

Required JSON schema (extra keys allowed):
{{
  "explanation": "string",
  "confidence_language": {{ "level": "string", "calibration": "string" }},
  "evidence_ids": ["string"],
  "what_would_change_my_mind": ["string"]
}}

If you provide hypotheses, use ONE of:
- "hypothesis": "string", "confidence": 0..1
OR
- "hypotheses": [{{"hypothesis":"string","confidence":0..1,"evidence_ids":["..."]}}]

Context:
belief = {json.dumps(belief, ensure_ascii=False)}
evidence = {json.dumps(evidence, ensure_ascii=False)}
trace_id = "{trace_id}"

Return ONLY the JSON object.
""".strip()

    # ---- call model ----
    response = _client.models.generate_content(
        model=MODEL_PRIMARY,
        contents=prompt,
    )

    raw_text = getattr(response, "text", None) or str(response)

    # ---- policy validate ----
    parsed_json: Optional[Dict[str, Any]] = None
    policy_status = "REJECTED"
    policy_error: Optional[str] = None

    try:
        parsed_json = PolicyGate.validate(raw_text)
        policy_status = "ACCEPTED"
    except PolicyViolation as e:
        policy_error = str(e)

    # ---- ALWAYS write ai_call_audit row ----
    ai_call_id: Optional[int] = None
    try:
        ai_call_id = record_ai_call(
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
        logger.exception("AI audit write failed (trace=%s) but continuing.", trace_id)

    # ---- Phase-1B: persist hypotheses into core table (ONLY if ACCEPTED) ----
    if policy_status == "ACCEPTED" and parsed_json is not None and ai_call_id is not None:
        try:
            belief_id = _best_effort_belief_id(belief, trace_id)
            inserted = persist_hypotheses(
                trace_id=trace_id,
                belief_id=belief_id,
                ai_call_audit_id=ai_call_id,
                validated_json=parsed_json,
            )
            if inserted:
                logger.info("Persisted %s hypothesis row(s) (trace=%s, belief_id=%s)", inserted, trace_id, belief_id)
        except Exception:
            logger.exception("Hypothesis persistence failed (trace=%s) but continuing.", trace_id)

    # ---- return accepted or fallback ----
    if policy_status == "ACCEPTED" and parsed_json is not None:
        logger.info("PolicyGate accepted Gemini output (trace=%s)", trace_id)
        return parsed_json

    logger.warning("PolicyGate rejected Gemini output (trace=%s): %s", trace_id, policy_error)

    return {
        "explanation": (
            "POLICYGATE_REJECTED: Model output failed Phase-1 policy validation. "
            "See ai_call_audit for raw_output and policy_error."
        ),
        "confidence_language": {"level": "unknown", "calibration": "blocked_by_policy_gate"},
        "evidence_ids": [],
        "what_would_change_my_mind": [
            "Return strictly valid JSON matching the schema, with evidence_ids, and no action/tool/DB language."
        ],
    }
