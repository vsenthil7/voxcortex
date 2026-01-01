from __future__ import annotations

import json
import hashlib
from typing import Any, Dict, Tuple


def canon_json(obj: Any) -> str:
    """
    Canonical JSON string:
    - deterministic key order
    - no whitespace
    - stable across runs
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,  # safety: datetime/UUID -> str
    )


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canon_and_hash(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Returns:
      - payload_canon_obj (dict)  (safe to store as JSONB)
      - sha256 hex of canonical JSON string
    """
    canon_str = canon_json(payload)
    return json.loads(canon_str), sha256_hex(canon_str)


def make_signature(trace_id: str, event_id: str, sha256: str, actor: str) -> str:
    """
    Deterministic provenance signature (NOT a secret signature).
    Used as a reproducible integrity marker for the audit spine.
    """
    material = f"{trace_id}|{event_id}|{sha256}|{actor}"
    return sha256_hex(material)
