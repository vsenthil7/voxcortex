import json
from datetime import datetime, timezone

from services.shared.crypto import sha256_hex
from services.shared.db import exec_sql
from services.shared.ids import new_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_snapshot(trace_id: str, payload: dict) -> dict:
    """
    Phase 0: store metadata + hash + payload (jsonb).
    Deterministic hashing is mandatory.
    """
    evidence_id = new_id("evd")
    created_at = now_iso()

    # Deterministic blob + hash
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha256_hex(blob)

    # IMPORTANT:
    # Use CAST(:payload AS jsonb) instead of :payload::jsonb (bind params + :: can break)
    exec_sql(
        """
        INSERT INTO evidence_snapshots(evidence_id, trace_id, sha256, created_at, payload)
        VALUES (:evidence_id, :trace_id, :sha256, :created_at, CAST(:payload AS jsonb))
        """,
        evidence_id=evidence_id,
        trace_id=trace_id,
        sha256=digest,
        created_at=created_at,
        payload=json.dumps(payload),
    )
    
    return {
        "evidence_id": evidence_id,
        "sha256": digest,
        "created_at": created_at,
    }