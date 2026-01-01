from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from services.shared.db import get_engine
from services.shared.logging import trace_logger
from services.shared.evidence_store import snapshot_evidence
from services.beliefcore.update_engine import deterministic_update
from services.cortexreasoner.gemini_reasoner import explain

log = logging.getLogger("phase0_worker")


def _jsonb(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def handle_canonical_event(event: dict) -> None:
    """
    Phase-0 Canonical Pipeline (STABLE)

    1. Evidence snapshot (Step-7 replay-immune)
    2. Deterministic belief update
    3. Belief upsert (WITH evidence_ids)
    4. Belief delta insert
    5. Explanation insert
    6. Audit log append
    """

    trace_id = event.get("trace_id", "trc_demo")
    event_id = event.get("event_id", "evt_demo")
    subject = event.get("subject", "service/api-gateway")
    hypothesis = event.get(
        "hypothesis",
        f"Issue affecting {subject}",
    )

    trace_logger(trace_id, "phase0_worker", "START")

    # ---------- Step-7: Canonical Evidence Snapshot ----------
    evidence_id, evidence_sha, signature = snapshot_evidence(
        trace_id=trace_id,
        payload=event,
    )

    # ---------- Deterministic Belief Update ----------
    prior = float(event.get("prior", 0.35))
    signal_strength = float(event.get("signal", 0.7))

    belief, delta = deterministic_update(
        trace_id,
        subject,
        hypothesis,
        prior,
        signal_strength,
        evidence_id,
    )

    now = datetime.now(timezone.utc)
    engine = get_engine()

    with engine.begin() as conn:

        # ---------- Belief UPSERT (FIXED) ----------
        conn.execute(
            text("""
                INSERT INTO beliefs (
                    belief_id,
                    trace_id,
                    subject,
                    hypothesis,
                    confidence,
                    evidence_ids,
                    updated_at
                )
                VALUES (
                    :belief_id,
                    :trace_id,
                    :subject,
                    :hypothesis,
                    :confidence,
                    CAST(:evidence_ids AS jsonb),
                    :updated_at
                )
                ON CONFLICT (belief_id) DO UPDATE
                SET
                    confidence = EXCLUDED.confidence,
                    evidence_ids = EXCLUDED.evidence_ids,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "belief_id": belief.belief_id,
                "trace_id": trace_id,
                "subject": subject,
                "hypothesis": hypothesis,
                "confidence": float(belief.confidence),
                "evidence_ids": json.dumps([evidence_id]),
                "updated_at": now,
            },
        )

        # ---------- Belief Delta (Idempotent) ----------
        conn.execute(
            text("""
                INSERT INTO belief_deltas (
                    belief_id,
                    trace_id,
                    from_conf,
                    to_conf,
                    reason,
                    created_at
                )
                VALUES (
                    :belief_id,
                    :trace_id,
                    :from_conf,
                    :to_conf,
                    :reason,
                    :created_at
                )
                ON CONFLICT DO NOTHING
            """),
            {
                "belief_id": delta.belief_id,
                "trace_id": trace_id,
                "from_conf": float(delta.from_conf),
                "to_conf": float(delta.to_conf),
                "reason": delta.reason,
                "created_at": now,
            },
        )
        # 3) Explanation (Phase-0 canon: trace_id + payload only)
        explanation_payload = {
            "belief_id": belief.belief_id,
            "subject": subject,
            "hypothesis": hypothesis,
            "confidence": float(belief.confidence),
            "evidence_ids": [evidence_id],
        }

        explanation = explain(
            trace_id,
            explanation_payload,
        )


        conn.execute(
            text("""
                INSERT INTO explanations (
                    belief_id,
                    trace_id,
                    explanation_json,
                    created_at
                )
                VALUES (
                    :belief_id,
                    :trace_id,
                    CAST(:explanation_json AS jsonb),
                    :created_at
                )
                ON CONFLICT DO NOTHING
            """),
            {
                "belief_id": belief.belief_id,
                "trace_id": trace_id,
                "explanation_json": json.dumps(explanation, ensure_ascii=False),
                "created_at": now,
            },
        )

        # ---------- Audit Log ----------
        conn.execute(
            text("""
                INSERT INTO audit_log (
                    trace_id,
                    actor,
                    action,
                    details,
                    created_at
                )
                VALUES (
                    :trace_id,
                    :actor,
                    :action,
                    CAST(:details AS jsonb),
                    :created_at
                )
            """),
            {
                "trace_id": trace_id,
                "actor": "phase0_worker",
                "action": "phase0_complete",
                "details": json.dumps(
                    {
                        "event_id": event_id,
                        "belief_id": belief.belief_id,
                        "evidence_id": evidence_id,
                        "evidence_sha256": evidence_sha,
                        "signature": signature,
                    },
                    ensure_ascii=False,
                ),
                "created_at": now,
            },
        )

    log.info("Phase-0 pipeline completed")


def main() -> None:
    fixture = {
        "trace_id": "trc_demo",
        "event_id": "evt_demo",
        "subject": "service/api-gateway",
        "hypothesis": "Issue affecting service/api-gateway",
        "prior": 0.35,
        "signal": 0.7,
        "raw": {},
    }

    handle_canonical_event(fixture)


if __name__ == "__main__":
    main()
