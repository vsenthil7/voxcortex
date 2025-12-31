from fastapi import FastAPI
from services.shared.db import exec_sql

app = FastAPI(title="VoxCortex AdminConsole", version="0.1.0")

@app.get("/v1/audit/{trace_id}")
def get_audit(trace_id: str):
    rows = exec_sql(
        "SELECT created_at, actor, action, details FROM audit_log WHERE trace_id=:trace_id ORDER BY created_at ASC",
        trace_id=trace_id
    ).mappings().all()
    return {"trace_id": trace_id, "events": list(rows)}

@app.get("/v1/evidence/{evidence_id}")
def get_evidence(evidence_id: str):
    row = exec_sql(
        "SELECT evidence_id, trace_id, sha256, created_at, payload FROM evidence_snapshots WHERE evidence_id=:evidence_id",
        evidence_id=evidence_id
    ).mappings().first()
    return {"evidence": dict(row) if row else None}
