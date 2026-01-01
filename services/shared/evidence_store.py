from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone

from sqlalchemy import text

from services.shared.db import get_engine


def snapshot_evidence(trace_id: str, payload: dict):
    """
    Phase-7 Canonical Evidence Snapshot
    - Deterministic hash (JSON canonical form)
    - Replay-immune (sha256 unique)
    - DB-safe (SQLAlchemy text() + :params)
    """

    # Canonical JSON
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    sha256 = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    engine = get_engine()

    with engine.begin() as conn:
        # 1️⃣ Evidence snapshot (idempotent on sha256)
        res = conn.execute(
            text("""
                INSERT INTO evidence_snapshots (
                    trace_id,
                    payload,
                    sha256,
                    created_at
                )
                VALUES (
                    :trace_id,
                    CAST(:payload AS jsonb),
                    :sha256,
                    :created_at
                )
                ON CONFLICT (sha256) DO UPDATE
                SET trace_id = EXCLUDED.trace_id
                RETURNING evidence_id
            """),
            {
                "trace_id": trace_id,
                "payload": canon,
                "sha256": sha256,
                "created_at": datetime.now(timezone.utc),
            },
        )

        evidence_id = res.scalar_one()

        # 2️⃣ Provenance record (also idempotent)
        signature = hashlib.sha256(
            f"{evidence_id}:{sha256}".encode("utf-8")
        ).hexdigest()

        conn.execute(
            text("""
                INSERT INTO evidence_provenance (
                    trace_id,
                    evidence_id,
                    sha256,
                    actor,
                    signature,
                    created_at
                )
                VALUES (
                    :trace_id,
                    :evidence_id,
                    :sha256,
                    :actor,
                    :signature,
                    :created_at
                )
                ON CONFLICT DO NOTHING
            """),
            {
                "trace_id": trace_id,
                "evidence_id": evidence_id,
                "sha256": sha256,
                "actor": "phase0_worker",
                "signature": signature,
                "created_at": datetime.now(timezone.utc),
            },
        )

    return evidence_id, sha256, signature
