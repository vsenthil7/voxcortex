# services/cortexreasoner/hypothesis_promoter.py
from typing import Any, Dict, Optional, Tuple, List

from sqlalchemy import text
from services.shared.db import get_engine


def _decision_from_confidence(conf: float) -> Tuple[str, str]:
    """
    Deterministic policy (system decides):
      >= 0.85  -> PROMOTE
      >= 0.60  -> HOLD
      <  0.60  -> REJECT
    """
    if conf >= 0.85:
        return "PROMOTE", "confidence>=0.85"
    if conf >= 0.60:
        return "HOLD", "0.60<=confidence<0.85"
    return "REJECT", "confidence<0.60"


def promote_latest_hypothesis_for_trace(
    *,
    trace_id: str,
    belief_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Load latest hypothesis for (trace_id, belief_id) and write deterministic promotion decision.
    Returns the promotion row (dict) or None if no hypothesis exists.
    """
    engine = get_engine()

    with engine.begin() as conn:
        # get latest hypothesis row
        row = conn.execute(
            text(
                """
                SELECT id, ai_call_audit_id, hypothesis, confidence, evidence_ids
                FROM hypotheses
                WHERE trace_id = :trace_id
                  AND belief_id = :belief_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"trace_id": trace_id, "belief_id": belief_id},
        ).fetchone()

        if not row:
            return None

        hypothesis_id = int(row[0])
        ai_call_audit_id = row[1]
        hypothesis_text = row[2]
        confidence = float(row[3])
        evidence_ids: List[str] = list(row[4] or [])

        decision, reason = _decision_from_confidence(confidence)

        # persist promotion decision (idempotent)
        conn.execute(
            text(
                """
                INSERT INTO belief_promotions (
                    trace_id,
                    belief_id,
                    hypothesis_id,
                    ai_call_audit_id,
                    decision,
                    decision_reason,
                    promoted_confidence,
                    evidence_ids
                )
                VALUES (
                    :trace_id,
                    :belief_id,
                    :hypothesis_id,
                    :ai_call_audit_id,
                    :decision,
                    :decision_reason,
                    :promoted_confidence,
                    :evidence_ids
                )
                ON CONFLICT (belief_id, hypothesis_id) DO NOTHING
                """
            ),
            {
                "trace_id": trace_id,
                "belief_id": belief_id,
                "hypothesis_id": hypothesis_id,
                "ai_call_audit_id": ai_call_audit_id,
                "decision": decision,
                "decision_reason": reason,
                "promoted_confidence": confidence,
                "evidence_ids": evidence_ids,
            },
        )

        return {
            "trace_id": trace_id,
            "belief_id": belief_id,
            "hypothesis_id": hypothesis_id,
            "ai_call_audit_id": ai_call_audit_id,
            "decision": decision,
            "decision_reason": reason,
            "promoted_confidence": confidence,
            "evidence_ids": evidence_ids,
        }
