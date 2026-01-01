# services/cortexreasoner/hypothesis_store.py
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from services.shared.db import get_engine


def _extract_hypotheses(obj: Dict[str, Any]) -> List[Tuple[str, Optional[float], List[str], Dict[str, Any]]]:
    """
    Returns list of tuples:
      (hypothesis_text, confidence, evidence_ids, payload)
    Accepts:
      - {"hypotheses":[{"hypothesis":"...", "confidence":0.8, "evidence_ids":[...]}], ...}
      - {"hypothesis":"...", "confidence":0.8, "evidence_ids":[...], ...}
    """
    out: List[Tuple[str, Optional[float], List[str], Dict[str, Any]]] = []

    if isinstance(obj.get("hypotheses"), list):
        for h in obj["hypotheses"]:
            if not isinstance(h, dict):
                continue
            text_val = h.get("hypothesis") or h.get("text") or h.get("statement")
            if not isinstance(text_val, str) or not text_val.strip():
                continue
            conf = h.get("confidence")
            conf_f: Optional[float] = None
            if isinstance(conf, (int, float)):
                conf_f = float(conf)
            eids = h.get("evidence_ids", obj.get("evidence_ids", []))
            if not isinstance(eids, list):
                eids = []
            eids_s = [str(x) for x in eids]
            out.append((text_val.strip(), conf_f, eids_s, h))

    else:
        text_val = obj.get("hypothesis")
        if isinstance(text_val, str) and text_val.strip():
            conf = obj.get("confidence")
            conf_f: Optional[float] = None
            if isinstance(conf, (int, float)):
                conf_f = float(conf)
            eids = obj.get("evidence_ids", [])
            if not isinstance(eids, list):
                eids = []
            eids_s = [str(x) for x in eids]
            out.append((text_val.strip(), conf_f, eids_s, obj))

    return out


def persist_hypotheses(
    *,
    trace_id: str,
    belief_id: str,
    ai_call_audit_id: int,
    validated_json: Dict[str, Any],
) -> int:
    """
    Persist hypotheses derived from a PolicyGate-ACCEPTED JSON payload.
    Returns number of rows inserted (dedup-safe via ux_hypotheses_dedup).
    """
    hyps = _extract_hypotheses(validated_json)
    if not hyps:
        return 0

    engine = get_engine()
    inserted = 0

    with engine.begin() as conn:
        for hypothesis_text, confidence, evidence_ids, payload in hyps:
            payload_text = json.dumps(payload, ensure_ascii=False)

            # ON CONFLICT prevents duplicates if same ai_call provides same hypothesis again
            res = conn.execute(
                text(
                    """
                    INSERT INTO hypotheses (
                        trace_id,
                        belief_id,
                        ai_call_audit_id,
                        hypothesis,
                        confidence,
                        evidence_ids,
                        payload
                    )
                    VALUES (
                        :trace_id,
                        :belief_id,
                        :ai_call_audit_id,
                        :hypothesis,
                        :confidence,
                        :evidence_ids,
                        CAST(:payload_text AS jsonb)
                    )
                    ON CONFLICT (ai_call_audit_id, hypothesis) DO NOTHING
                    """
                ),
                {
                    "trace_id": trace_id,
                    "belief_id": belief_id,
                    "ai_call_audit_id": ai_call_audit_id,
                    "hypothesis": hypothesis_text,
                    "confidence": confidence,
                    "evidence_ids": evidence_ids,
                    "payload_text": payload_text,
                },
            )
            # rowcount is 1 if inserted, 0 if skipped
            inserted += int(res.rowcount or 0)

    return inserted
