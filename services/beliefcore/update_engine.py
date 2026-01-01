from datetime import datetime, timezone
import uuid

# =========================================
# Internal deterministic update (PRIVATE)
# =========================================

def _deterministic_update(
    subject,
    trace_id,
    hypothesis,
    prior,
    signal_strength,
    evidence_id,
):
    """
    INTERNAL FUNCTION — positional args ONLY
    """

    belief_id = f"blf_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)

    # Deterministic confidence update
    to_conf = round(
        min(1.0, max(0.0, prior + (signal_strength * (1 - prior)))),
        3
    )

    belief = Belief(
        belief_id=belief_id,
        trace_id=trace_id,
        subject=subject,
        hypothesis=hypothesis,
        confidence=to_conf,
        updated_at=now,
        evidence=[EvidenceRef(evidence_id=evidence_id)],
    )

    delta = BeliefDelta(
        belief_id=belief_id,
        trace_id=trace_id,
        from_conf=prior,
        to_conf=to_conf,
        reason=f"deterministic_update(prior={prior}, signal={signal_strength})",
        created_at=now,
    )

    return belief, delta


# =========================================
# PUBLIC CANONICAL API
# =========================================

def deterministic_update(
    subject: str,
    trace_id: str,
    hypothesis: str,
    prior: float,
    signal_strength: float,
    evidence_id: str,
):
    """
    CANONICAL ENTRYPOINT — workers import ONLY this
    """
    return _deterministic_update(
        subject,
        trace_id,
        hypothesis,
        prior,
        signal_strength,
        evidence_id,
    )


# =========================================
# Domain Objects (Serializable)
# =========================================

class EvidenceRef:
    def __init__(self, evidence_id: str):
        self.evidence_id = evidence_id

    def to_dict(self):
        return {"evidence_id": self.evidence_id}


class Belief:
    def __init__(
        self,
        belief_id,
        trace_id,
        subject,
        hypothesis,
        confidence,
        updated_at,
        evidence,
    ):
        self.belief_id = belief_id
        self.trace_id = trace_id
        self.subject = subject
        self.hypothesis = hypothesis
        self.confidence = confidence
        self.updated_at = updated_at
        self.evidence = evidence

    def to_dict(self):
        return {
            "belief_id": self.belief_id,
            "trace_id": self.trace_id,
            "subject": self.subject,
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
            "updated_at": self.updated_at.isoformat(),
            "evidence": [e.to_dict() for e in self.evidence],
        }


class BeliefDelta:
    def __init__(
        self,
        belief_id,
        trace_id,
        from_conf,
        to_conf,
        reason,
        created_at,
    ):
        self.belief_id = belief_id
        self.trace_id = trace_id
        self.from_conf = from_conf
        self.to_conf = to_conf
        self.reason = reason
        self.created_at = created_at

    def to_dict(self):
        return {
            "belief_id": self.belief_id,
            "trace_id": self.trace_id,
            "from_conf": self.from_conf,
            "to_conf": self.to_conf,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }
