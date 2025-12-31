import json
import logging

from services.shared.logging import setup_logging
from services.shared.db import exec_sql
from services.beliefcore.update_engine import deterministic_update
from services.evidencevault.snapshot import create_snapshot
from services.evidencevault.provenance import sign_provenance
from services.cortexreasoner.explainer import explain
from services.voiceio.tts_elevenlabs import tts


setup_logging()
log = logging.getLogger("phase0_worker")

def handle_canonical_event(canonical: dict):
    trace_id = canonical["trace_id"]
    tlog = logging.getLogger(__name__)

    event_id = canonical["event_id"]
    subject = f"service/{canonical.get('normalized', {}).get('service', 'unknown')}"
    hypothesis = f"Potential incident affecting {subject}"
    prior = 0.35
    signal_strength = 0.7 if canonical.get("severity") in ("high", "critical") else 0.4

    belief, delta = deterministic_update(
        subject=subject,
        trace_id=trace_id,
        hypothesis=hypothesis,
        prior=prior,
        signal_strength=signal_strength,
        evidence_id=event_id
    )

    # Evidence snapshot (belief + delta + event pointer)
    snap_payload = {
        "event_id": event_id,
        "belief": belief.model_dump(),
        "delta": delta.model_dump(),
    }
    snap = create_snapshot(trace_id=trace_id, payload=snap_payload)
    prov = sign_provenance(trace_id=trace_id, evidence_id=snap["evidence_id"], sha256=snap["sha256"], actor="phase0_worker")

    # Persist belief + delta
    exec_sql(
        """
        INSERT INTO beliefs(
            belief_id, trace_id, subject, hypothesis,
            confidence, updated_at, evidence_ids
        )
        VALUES (
            :belief_id, :trace_id, :subject, :hypothesis,
            :confidence, :updated_at, CAST(:evidence_ids AS jsonb)
        )
        ON CONFLICT (belief_id)
        DO UPDATE SET
            confidence = EXCLUDED.confidence,
            updated_at = EXCLUDED.updated_at,
            evidence_ids = EXCLUDED.evidence_ids
        """,
        belief_id=belief.belief_id,
        trace_id=belief.trace_id,
        subject=belief.subject,
        hypothesis=belief.hypothesis,
        confidence=belief.confidence,
        updated_at=belief.updated_at,
        evidence_ids=json.dumps([e.evidence_id for e in belief.evidence]),
    )

    exec_sql(
        """
        INSERT INTO belief_deltas(belief_id, trace_id, from_conf, to_conf, reason)
        VALUES (:belief_id, :trace_id, :from_conf, :to_conf, :reason)
        """,
        belief_id=delta.belief_id,
        trace_id=trace_id,
        from_conf=delta.from_conf,
        to_conf=delta.to_conf,
        reason=delta.reason,
    )

    # LLM explanation (bounded by evidence IDs)
    expl = explain(
        belief=belief.model_dump(),
        evidence=[{"evidence_id": event_id}, {"evidence_id": snap["evidence_id"], "sha256": snap["sha256"]}]
    )

    # Voice output
    audio = tts(text=str(expl.get("explanation", "")), confidence=float(belief.confidence))

    # Store explanation + voice artifact metadata (Phase 0: store bytes length only)
    exec_sql(
        """
        INSERT INTO explanations(
            trace_id, belief_id, explanation_json, audio_bytes_len
        )
        VALUES (
            :trace_id,
            :belief_id,
            CAST(:explanation_json AS jsonb),
            :audio_bytes_len
        )
        """,
        trace_id=trace_id,
        belief_id=belief.belief_id,
        explanation_json=json.dumps(expl),
        audio_bytes_len=len(audio),
    )


    # Audit log (FINAL JSONB FIX)
    exec_sql(
        """
        INSERT INTO audit_log(
            trace_id, actor, action, details
        )
        VALUES (
            :trace_id,
            :actor,
            :action,
            CAST(:details AS jsonb)
        )
        """,
        trace_id=trace_id,
        actor="phase0_worker",
        action="belief+evidence+explain",
        details=json.dumps({
            "event_id": event_id,
            "belief_id": belief.belief_id,
            "snapshot_id": snap["evidence_id"],
            "signature": prov["signature"],
        }),
    )

    tlog.info("Phase0 complete")


def main():
    """
    Phase 0 runner:
    - In GCP: wire to Pub/Sub push subscription -> Cloud Run endpoint OR use subscriber client.
    - For local: call handle_canonical_event(...) with a fixture.
    """
    fixture = {
        "event_id": "evt_demo",
        "trace_id": "trc_demo",
        "source": "datadog",
        "event_type": "alert",
        "occurred_at": "2025-12-31T13:31:00Z",
        "severity": "high",
        "normalized": {"service": "api-gateway", "region": "europe-west2", "message": "Latency spike"}
    }
    handle_canonical_event(fixture)

if __name__ == "__main__":
    main()
