from fastapi import FastAPI, Header
from services.signalmesh.schemas import IngestEvent
from services.signalmesh.normalizer import normalize
from services.shared.ids import new_id
from services.shared.db import exec_sql
from services.shared.logging import setup_logging, TraceAdapter
from services.shared.config import settings

import logging
import json
import os

# Pub/Sub is optional for local dev.
# We only initialize if explicitly enabled (prevents ADC errors locally).
try:
    from google.cloud import pubsub_v1
except Exception:
    pubsub_v1 = None

setup_logging()
log = TraceAdapter(logging.getLogger("signalmesh"), {"trace_id": "boot"})

app = FastAPI(title="VoxCortex SignalMesh", version="0.1.0")

ENABLE_PUBSUB = os.getenv("ENABLE_PUBSUB", "false").lower() == "true"

_publisher = None
if ENABLE_PUBSUB and pubsub_v1:
    _publisher = pubsub_v1.PublisherClient()


def publish_ingest(event_dict: dict) -> None:
    if not _publisher or not settings.gcp_project:
        # local dev: no-op publish, still deterministic
        return
    topic_path = _publisher.topic_path(settings.gcp_project, settings.pubsub_topic_ingest)
    data = json.dumps(event_dict).encode("utf-8")
    _publisher.publish(topic_path, data=data)


@app.post("/v1/ingest")
def ingest(evt: IngestEvent, x_trace_id: str | None = Header(default=None)):
    trace_id = x_trace_id or new_id("trc")
    tlog = TraceAdapter(logging.getLogger("signalmesh"), {"trace_id": trace_id})

    canonical = normalize(evt, trace_id=trace_id)

    # Store raw + canonical deterministically
    exec_sql(
        """
        INSERT INTO events(event_id, trace_id, source, event_type, occurred_at, severity, raw_payload, canonical_payload)
        VALUES (
            :event_id, :trace_id, :source, :event_type, :occurred_at, :severity,
            CAST(:raw_payload AS jsonb),
            CAST(:canonical_payload AS jsonb)
        )
        """,
        event_id=canonical.event_id,
        trace_id=canonical.trace_id,
        source=canonical.source,
        event_type=canonical.event_type,
        occurred_at=canonical.occurred_at,
        severity=canonical.severity,
        raw_payload=json.dumps(evt.model_dump()),
        canonical_payload=json.dumps(canonical.model_dump()),
    )

    publish_ingest(canonical.model_dump())

    # Audit
    exec_sql(
        """
        INSERT INTO audit_log(trace_id, actor, action, details)
        VALUES (:trace_id, :actor, :action, CAST(:details AS jsonb))
        """,
        trace_id=trace_id,
        actor="signalmesh",
        action="ingest",
        details=json.dumps({"event_id": canonical.event_id}),
    )

    tlog.info("ingested event", extra={"trace_id": trace_id})
    return {"ok": True, "trace_id": trace_id, "event_id": canonical.event_id}
