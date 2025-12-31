import json
from datetime import datetime, timezone

from services.beliefcore.models import Belief, BeliefDelta, EvidenceRef
from services.shared.ids import new_id
from services.shared.db import exec_sql


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def deterministic_update(
    subject: str,
    trace_id: str,
    hypothesis: str,
    prior: float,
    signal_strength: float,
    evidence_id: str,
) -> tuple[Belief, BeliefDelta]:
    """
    Phase 0 deterministic belief update.
    No AI. No heuristics. Fully reproducible.
    """
    to_conf = max(0.0, min(1.0, prior + 0.35 * signal_strength))
    belief_id = new_id("blf")
    updated_at = now_iso()

    belief = Belief(
        belief_id=belief_id,
        trace_id=trace_id,
        subject=subject,
        hypothesis=hypothesis,
        confidence=to_conf,
        evidence=[
            EvidenceRef(
                evidence_id=evidence_id,
                kind="event",
                pointer={"event_id": evidence_id},
            )
        ],
        updated_at=updated_at,
    )

    delta = BeliefDelta(
        belief_id=belief_id,
        from_conf=prior,
        to_conf=to_conf,
        reason=f"deterministic_update(prior={prior}, signal={signal_strength})",
    )

    # ✅ CANONICAL SQL — NO ::jsonb, NO %(), NO $1
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
        """,
        belief_id=belief_id,
        trace_id=trace_id,
        subject=subject,
        hypothesis=hypothesis,
        confidence=to_conf,
        updated_at=updated_at,
        evidence_ids=json.dumps([e.evidence_id for e in belief.evidence]),
    )

    exec_sql(
        """
        INSERT INTO belief_deltas(
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
        """,
        belief_id=belief_id,
        trace_id=trace_id,
        from_conf=prior,
        to_conf=to_conf,
        reason=delta.reason,
        created_at=updated_at,
    )

    return belief, delta
