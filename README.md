# VoxCortex

Real-time cognitive voice intelligence with deterministic belief tracking, semantic idempotency, and audit-safe execution.

---

## System Intent

VoxCortex is a deterministic cognitive backend designed to convert raw events into:

- immutable evidence
- stable beliefs
- causal belief deltas
- bounded, human-readable explanations
- reproducible audit trails

The system is built to be replay-safe and idempotent by construction.

This repository reflects the **actual implemented code**, not future design.

---

## Repository Scope (Truth-Bound)

This repository contains:

- a single canonical execution worker
- deterministic belief update logic
- bounded LLM reasoning
- evidence provenance handling
- shared infrastructure utilities

No UI, streaming fan-out, or orchestration layer is included.

---

## Repository Structure

apps/      - Admin/API surface  
infra/     - SQL initialization  
services/  - Cognitive core services  
workers/   - Canonical execution worker  

---

## PHASE-0 - Canonical Ingestion and Belief Formation

Purpose:  
Provide a deterministic, replay-safe pipeline from event ingestion to belief creation.

---

### Canonical Worker

File:
workers/phase0_worker.py

What it does:
- Acts as the single entry point for canonical events
- Executes logic in a fixed order:
  1. Evidence snapshot
  2. Belief creation or update
  3. Belief delta calculation
  4. Explanation generation
  5. Audit logging

Properties:
- Deterministic execution
- Safe to re-run
- No side effects outside the database layer

---

### Evidence Handling

Files:
services/evidencevault/snapshot.py  
services/evidencevault/provenance.py  

Behavior:
- Incoming event data is hashed (SHA256)
- Evidence records are immutable once written
- Provenance information is stored alongside each snapshot

Purpose:
- Create a cryptographic and forensic anchor for all downstream logic

---

### Belief Model and Update Engine

Files:
services/beliefcore/models.py  
services/beliefcore/update_engine.py  

Behavior:
- Beliefs are identified by semantic keys (trace, subject, hypothesis)
- Confidence updates are deterministic
- Same input always produces the same output
- No randomness or time-based drift

The update engine produces:
- an updated belief state
- a corresponding belief delta

---

### Belief Delta Tracking

Belief deltas represent:
- prior confidence
- updated confidence
- the reason for the transition

Deltas form a causal chain that explains how a belief evolved over time.

---

### Explanation Generation (Bounded)

Files:
services/cortexreasoner/gemini_reasoner.py  
services/cortexreasoner/explainer.py  

Behavior:
- Uses a bounded Gemini call for explanation generation
- Falls back to a deterministic stub if no API key is present
- Explanation output never feeds back into belief math

Purpose:
- Human interpretability only
- No influence on ground truth

---

### Shared Infrastructure

Files:
services/shared/config.py  
services/shared/db.py  
services/shared/logging.py  
services/shared/crypto.py  
services/shared/ids.py  

Purpose:
- Configuration loading
- Database access
- Trace-safe logging
- ID and hash utilities

Logging is stabilized to ensure:
- consistent trace IDs
- no runtime formatter failures
- safe interaction with HTTP and LLM clients

---

## PHASE-1 - Semantic Idempotency Hardening (Logical)

Purpose:  
Prevent logical duplication during correct replays.

This phase is implemented as **logic and constraints inside existing code**, not as separate migration files.

Guarantees:
- A belief is not duplicated for the same semantic identity
- Replayed events do not create duplicate belief deltas
- Deterministic update paths are enforced consistently

---

## Admin and Signal Interfaces

Files:
apps/adminconsole/api.py  
services/signalmesh/app.py  
services/signalmesh/normalizer.py  
services/signalmesh/schemas.py  

Purpose:
- Provide normalized signal ingestion
- Define schemas for structured input
- Prepare future integration points

These components do not alter belief math.

---

## Database Initialization

File:
infra/sql/001_init.sql  

Purpose:
- Initial schema setup
- Baseline tables required by the system

No other migrations are included in this repository.

---

## Current Boundary

This repository intentionally stops at:
- deterministic ingestion
- belief math
- semantic idempotency
- audit safety

Anything beyond this is out of scope.

---

## License

MIT
