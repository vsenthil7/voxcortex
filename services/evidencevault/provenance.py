import json
from services.shared.crypto import hmac_sign_hex
from services.shared.db import exec_sql
from services.shared.config import settings
from datetime import datetime, timezone

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sign_provenance(trace_id: str, evidence_id: str, sha256: str, actor: str) -> dict:
    msg = json.dumps(
        {"trace_id": trace_id, "evidence_id": evidence_id, "sha256": sha256, "actor": actor},
        sort_keys=True
    ).encode("utf-8")

    sig = hmac_sign_hex(settings.evidence_signing_key_b64, msg)

    exec_sql(
        """
        INSERT INTO evidence_provenance(trace_id, evidence_id, sha256, actor, signature, created_at)
        VALUES (:trace_id, :evidence_id, :sha256, :actor, :signature, :created_at)
        """,
        trace_id=trace_id,
        evidence_id=evidence_id,
        sha256=sha256,
        actor=actor,
        signature=sig,
        created_at=now_iso(),
    )
    return {"signature": sig, "created_at": now_iso()}
