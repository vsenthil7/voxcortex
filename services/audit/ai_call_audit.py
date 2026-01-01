# services/audit/ai_call_audit.py
import json
import hashlib
from typing import Any, Optional, Dict

from sqlalchemy import text
from services.shared.db import get_engine


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def record_ai_call(
    *,
    trace_id: str,
    phase: str,
    model_name: str,
    prompt: str,
    raw_output: str,
    parsed_json: Optional[Dict[str, Any]],
    policy_status: str,
    policy_error: Optional[str],
) -> int:
    """
    Writes an immutable audit row for EVERY model call and returns inserted id.
    - raw_output: exact model output (string)
    - parsed_json: dict or None (stored as jsonb; NULL if None)
    """
    engine = get_engine()

    prompt_hash = _sha256(prompt or "")
    prompt_preview = (prompt[:4000] if prompt else "")  # bounded

    parsed_json_text = None
    if parsed_json is not None:
        parsed_json_text = json.dumps(parsed_json, ensure_ascii=False)

    with engine.begin() as conn:
        row_id = conn.execute(
            text(
                """
                INSERT INTO ai_call_audit (
                    trace_id,
                    phase,
                    model_name,
                    prompt_hash,
                    prompt_preview,
                    raw_output,
                    parsed_json,
                    policy_status,
                    policy_error
                )
                VALUES (
                    :trace_id,
                    :phase,
                    :model_name,
                    :prompt_hash,
                    :prompt_preview,
                    :raw_output,
                    CAST(:parsed_json_text AS jsonb),
                    :policy_status,
                    :policy_error
                )
                RETURNING id
                """
            ),
            {
                "trace_id": trace_id,
                "phase": phase,
                "model_name": model_name,
                "prompt_hash": prompt_hash,
                "prompt_preview": prompt_preview,
                "raw_output": raw_output,
                "parsed_json_text": parsed_json_text,  # may be None → CAST(NULL AS jsonb) works
                "policy_status": policy_status,
                "policy_error": policy_error,
            },
        ).scalar_one()

    return int(row_id)
