from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class IngestEvent(BaseModel):
    source: str = Field(..., description="connector source, e.g. datadog/jira/siem")
    event_type: str = Field(..., description="canonical-ish type, e.g. alert, incident, change")
    occurred_at: str = Field(..., description="ISO timestamp string")
    severity: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

class CanonicalEvent(BaseModel):
    event_id: str
    trace_id: str
    source: str
    event_type: str
    occurred_at: str
    severity: Optional[str] = None
    normalized: Dict[str, Any] = Field(default_factory=dict)
