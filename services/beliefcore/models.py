from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class EvidenceRef(BaseModel):
    evidence_id: str
    kind: str = Field(..., description="event|snapshot|external")
    pointer: Dict[str, str] = Field(default_factory=dict)

class Belief(BaseModel):
    belief_id: str
    trace_id: str
    subject: str = Field(..., description="e.g. service/api-gateway or site/manchester-dc")
    hypothesis: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    updated_at: str

class BeliefDelta(BaseModel):
    belief_id: str
    from_conf: float
    to_conf: float
    reason: str
