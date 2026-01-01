# VoxCortex

Real-time cognitive voice intelligence with deterministic belief tracking, semantic idempotency, and full auditability.

---

## System Intent

VoxCortex is designed as a deterministic cognitive spine that converts raw events into:

- immutable evidence
- stable beliefs
- causal belief deltas
- bounded explanations
- full forensic audit trails

The system is replay-safe, idempotent, and auditable by construction.

This repository captures the Phase-0 canonical pipeline and Phase-1 semantic hardening, as implemented and locked.

---

## Canonical Build Status

As of: 01/01/2026 15:27  
State: Stable, replay-safe, non-drifting

| Component            | Status |
|---------------------|--------|
| Phase-0 Worker      | OK     |
| Evidence Snapshots  | OK     |
| Beliefs             | OK     |
| Belief Deltas       | OK     |
| Explanations        | OK     |
| Audit Log           | OK     |
| Replays             | OK     |

---

## PHASE-0 - Canonical Ingestion and Ground Truth Spine

Purpose:  
Create a deterministic, replay-safe, auditable pipeline from raw events to belief to explanation.

---

### 1. Canonical Event Handling

File:
workers/phase0_worker.py

What exists:
- Single entry point: handle_canonical_event(fixture)
- Fixed trace_id (trc_demo) for repeatability
- Deterministic execution order:
  1. Evidence snapshot
  2. Belief create or update
  3. Belief delta
  4. Explanation generation
  5. Audit log write

Key properties:
- Re-runnable
- No side effects outside database
- Safe under retries

---

### 2. Evidence Snapshot and Provenance

Tables:
- evidence_snapshots
- evidence_provenance

Enforced behavior:
- Every event hashed using SHA256
- Evidence content is immutable
- Actor and signature stored per snapshot

Why it matters:
- Evidence is cryptographically anchored
- Hash is the root of trust for downstream logic

---

### 3. Belief Record (Ground Truth)

Table:
- beliefs

Semantic identity:
- (trace_id, subject, hypothesis) defines uniqueness

Behavior:
- Deterministic confidence updates
- Evidence IDs stored as JSONB
- INSERT ... ON CONFLICT DO UPDATE

Guarantee:
- No duplicate beliefs survive cleanup

---

### 4. Deterministic Belief Update Engine

File:
services/beliefcore/update_engine.py

Logic:
- _deterministic_update(prior, signal)
- No randomness
- Same input always produces same output

Produces:
- Updated belief
- Corresponding belief delta

---

### 5. Belief Delta (Causality Trail)

Table:
- belief_deltas

Captured:
- from_conf to to_conf
- Reason string (example: deterministic_update(prior=0.35, signal=0.7))
- Timestamped causal chain

---

### 6. Explanation Generation (LLM-Bounded)

File:
services/cortexreasoner/gemini_reasoner.py

Behavior:
- Gemini call is bounded
- Deterministic stub if API key is missing
- Output stored verbatim

Table:
- explanations

Safety property:
- Explanations never feed back into belief math
- Human-readable only

---

### 7. Audit Log (Compliance Spine)

Table:
- audit_log

Recorded:
- actor
- action
- snapshot_id
- belief_id
- timestamp

Guarantee:
- Full forensic trace from event to belief to explanation

---

## PHASE-1 - Semantic Idempotency Hardening

Purpose:  
Prevent logical duplication even under correct replay.

---

### Step-1 - Belief Deduplication

Action:
- SQL cleanup of duplicate beliefs per (trace_id, subject)
- Retained newest updated_at

Result:
- Exactly one active belief per semantic subject

---

### Step-2 - Belief Delta Deduplication

Action:
- Removed duplicate deltas per belief
- Kept latest causal transition

Result:
- Delta table expresses true belief evolution

---

### Step-3 - Strict Semantic Idempotency

Database script:
- step6_semantic_idempotency.sql

Constraint:
- UNIQUE (belief_id, from_conf, to_conf, reason)

Guarantee:
- Same update cannot be recorded twice

---

### Step-4 - Time-Windowed Delta Idempotency (Option B)

Database script:
- step6b_time_window_idempotency.sql

Added:
- window_bucket (60 seconds)

Why:
- Allows controlled re-evaluation
- Blocks rapid replay storms

---

### Step-5 - Update Engine Alignment

Changes:
- Unified deterministic update path
- Removed mismatched function signatures
- Explicit call to _deterministic_update

Outcome:
- Worker and engine contract is stable

---

### Step-6 - Logging Contract Stabilization

File:
services/shared/logging.py

Fixed:
- trace_logger signature
- Missing trace_id formatter errors
- Safe logging across Gemini and HTTPX

Result:
- Clean logs
- No runtime logging failures

---

## Repository Structure

apps/      - Admin and API surfaces  
infra/     - SQL and infrastructure  
services/  - Cognitive core services  
workers/   - Canonical execution workers  

---

## Current Scope Boundary

This repository intentionally stops at:
- deterministic ingestion
- belief math
- idempotency
- auditability

No UI, orchestration layer, or real-time stream fan-out is introduced yet.

---

## License

MIT
