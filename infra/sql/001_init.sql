CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  source TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  severity TEXT,
  raw_payload JSONB NOT NULL,
  canonical_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS beliefs (
  belief_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  evidence_ids JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS belief_deltas (
  id BIGSERIAL PRIMARY KEY,
  belief_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  from_conf DOUBLE PRECISION NOT NULL,
  to_conf DOUBLE PRECISION NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_snapshots (
  evidence_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_provenance (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  actor TEXT NOT NULL,
  signature TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS explanations (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  belief_id TEXT NOT NULL,
  explanation_json JSONB NOT NULL,
  audio_bytes_len INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  details JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
