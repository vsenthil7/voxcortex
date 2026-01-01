import json
import logging
from datetime import timezone

from services.shared.logging import trace_logger
from services.shared.db import exec_sql
from services.beliefcore.update_engine import deterministic_update
from services.evidencevault.snapshot import create_snapshot
from services.evidencevault.provenance import sign_provenance
from services.cortexreasoner.explainer import explain
from services.voiceio.tts_elevenlabs import tts


log = logging.getLogger("phase0_worker")


def handle_canonical_event(canonical: dict):
    trace_id = canonical["trace_id"]

    # START TRACE
    log = trace_logger(trace_id, "phase0_worker")
    log.info("START")


    event_id = canonical["event_id"]
    subject = f"service/{canonical.get('normalized', {}).get('service', 'unknown')}"
    hypothesis = f"Potential incident affecting {subject}"

    prior = 0.35
    signal_strength = 0.7 if canonical.get("severity") in ("high", "critical") else 0.4

    # -------------------------------
    # Belief Update (Deterministic)
    # -------------------------------
    belief, delta = deterministic_update(
        subject=subject,
        trace_id=trace_id,
        hypothesis=hypothesis,
        prior=prior,
        signal_strength=signal_strength,
        evidence_id=event_id,
    )

    # -------------------------------
    # Evidence Snapshot + Provenance
    # -------------------------------
    snap_payload = {
        "event_id": event_id,
        "belief": belief.to_dict(),
        "delta": delta.to_dict(),
    }

    snap = create_snapshot(trace_id=trace_id, payload=snap_payload)

    prov = sign_provenance(
        trace_id=trace_id,
        evidence_id=snap["evidence_id"],
        sha256=snap["sha256"],
        actor="phase0_worker",
    )

    # -------------------------------
    # Persist Belief (JSONB FIX)
    # -------------------------------
    exec_sql(
        """
        INSERT INTO beliefs (
            belief_id, trace_id, subject, hypothesis,
            confidence, updated_at, evidence_ids
        )
        VALUES (
            :belief_id, :trace_id, :subject, :hypothesis,
            :confidence, :updated_at, CAST(:evidence_ids AS jsonb)
        )
        ON CONFLICT (belief_id) DO UPDATE
        SET confidence = EXCLUDED.confidence,
            updated_at = EXCLUDED.updated_at,
            evidence_ids = EXCLUDED.evidence_ids
        """,
        belief_id=belief.belief_id,
        trace_id=belief.trace_id,
        subject=belief.subject,
        hypothesis=belief.hypothesis,
        confidence=belief.confidence,
        updated_at=belief.updated_at.astimezone(timezone.utc),
        evidence_ids=json.dumps([event_id]),  # ✅ FIXED
    )

    # -------------------------------
    # Persist Delta (Idempotent)
    # -------------------------------
    exec_sql(
        """
        INSERT INTO belief_deltas (
            belief_id, trace_id, from_conf, to_conf, reason
        )
        VALUES (
            :belief_id, :trace_id, :from_conf, :to_conf, :reason
        )
        ON CONFLICT DO NOTHING
        """,
        belief_id=delta.belief_id,
        trace_id=trace_id,
        from_conf=delta.from_conf,
        to_conf=delta.to_conf,
        reason=delta.reason,
    )

    # -------------------------------
    # LLM Explanation (Bounded)
    # -------------------------------
    expl = explain(
        belief=belief.to_dict(),
        evidence=[
            {"evidence_id": event_id},
            {"evidence_id": snap["evidence_id"], "sha256": snap["sha256"]},
        ],
    )

    # -------------------------------
    # Voice Output
    # -------------------------------
    audio = tts(
        text=str(expl.get("explanation", "")),
        confidence=float(belief.confidence),
    )

    exec_sql(
        """
        INSERT INTO explanations (
            trace_id, belief_id, explanation_json, audio_bytes_len
        )
        VALUES (
            :trace_id, :belief_id, CAST(:explanation_json AS jsonb), :audio_bytes_len
        )
        """,
        trace_id=trace_id,
        belief_id=belief.belief_id,
        explanation_json=json.dumps(expl),
        audio_bytes_len=len(audio),
    )

    # -------------------------------
    # Audit Log
    # -------------------------------
    exec_sql(
        """
        INSERT INTO audit_log (
            trace_id, actor, action, details
        )
        VALUES (
            :trace_id, :actor, :action, CAST(:details AS jsonb)
        )
        """,
        trace_id=trace_id,
        actor="phase0_worker",
        action="belief+evidence+explain",
        details=json.dumps(
            {
                "event_id": event_id,
                "belief_id": belief.belief_id,
                "snapshot_id": snap["evidence_id"],
                "signature": prov["signature"],
            }
        ),
    )

    log.info("Phase0 complete")


def main():
    fixture = {
        "event_id": "evt_demo",
        "trace_id": "trc_demo",
        "source": "datadog",
        "event_type": "alert",
        "occurred_at": "2025-12-31T13:31:00Z",
        "severity": "high",
        "normalized": {
            "service": "api-gateway",
            "region": "europe-west2",
            "message": "Latency spike",
        },
    }

    handle_canonical_event(fixture)


if __name__ == "__main__":
    main()
