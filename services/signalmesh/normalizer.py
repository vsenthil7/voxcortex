from services.shared.ids import new_id
from services.signalmesh.schemas import IngestEvent, CanonicalEvent

def normalize(ingest: IngestEvent, trace_id: str) -> CanonicalEvent:
    # Deterministic normalization only: schema shaping + safe defaults
    event_id = new_id("evt")
    normalized = {
        "raw_keys": sorted(list(ingest.payload.keys())),
        "message": str(ingest.payload.get("message") or ingest.payload.get("title") or ""),
        "service": ingest.payload.get("service") or ingest.payload.get("app") or "unknown",
        "region": ingest.payload.get("region") or "unknown",
    }

    return CanonicalEvent(
        event_id=event_id,
        trace_id=trace_id,
        source=ingest.source,
        event_type=ingest.event_type,
        occurred_at=ingest.occurred_at,
        severity=ingest.severity,
        normalized=normalized
    )
