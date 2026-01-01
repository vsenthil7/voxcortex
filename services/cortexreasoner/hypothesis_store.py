# services/cortexreasoner/hypothesis_store.py
import json
import hashlib
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from services.shared.db import get_engine


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def persist_hypothesis(
    *,
    trace_id: str,
    belief_id: str,
    ai_call_audit_id: Optional[int],
    hypothesis: str,
    confidence: float,
    evidence_ids: List[str],
    raw_json: Dict[str, Any],
) -> None:
    """
    Persist Phase-1 hypothesis into hypotheses table.
    Dedup enforced by your unique index (trace_id + belief_id + hypothesis_hash).
    """
    engine = get_engine()

    hypothesis_hash = _sha256(hypothesis.strip().lower())
    evidence_ids_text = [str(x) for x in evidence_ids]
    raw_json_text = json.dumps(raw_json, ensure_ascii=False)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO hypotheses (
                    trace_id,
                    belief_id,
                    ai_call_audit_id,
                    hypothesis_hash,
                    hypothesis,
                    confidence,
                    evidence_ids,
                    raw_json
                )
                VALUES (
                    :trace_id,
                    :belief_id,
                    :ai_call_audit_id,
                    :hypothesis_hash,
                    :hypothesis,
                    :confidence,
                    :evidence_ids,
                    CAST(:raw_json AS jsonb)
                )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "trace_id": trace_id,
                "belief_id": belief_id,
                "ai_call_audit_id": ai_call_audit_id,
                "hypothesis_hash": hypothesis_hash,
                "hypothesis": hypothesis,
                "confidence": float(confidence),
                "evidence_ids": evidence_ids_text,
                "raw_json": raw_json_text,
            },
        )
