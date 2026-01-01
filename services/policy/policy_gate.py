# services/policy/policy_gate.py
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List


class PolicyViolation(Exception):
    pass


@dataclass(frozen=True)
class PolicyGate:
    """
    Phase-1 policy:
    - Must return JSON object
    - Must include required keys
    - Must not contain action/tool/db instructions
    """

    REQUIRED_KEYS = (
        "explanation",
        "confidence_language",
        "evidence_ids",
        "what_would_change_my_mind",
    )

    # cheap but effective guardrails (you can expand later)
    DISALLOWED_PATTERNS = (
        r"\b(run|execute|delete|drop|insert|update|commit)\b",
        r"\b(psql|sql|database|db|postgres|pg_)\b",
        r"\b(curl|wget|pip install|apt-get)\b",
        r"\b(call tool|use tool|invoke)\b",
        r"\b(write to|save to)\b",
    )

    @staticmethod
    def _strip_code_fences(s: str) -> str:
        s = s.strip()
        # ```json ... ``` or ``` ... ```
        if s.startswith("```"):
            # remove first fence line
            s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
            # remove trailing ```
            s = re.sub(r"\s*```$", "", s)
        return s.strip()

    @staticmethod
    def _extract_json_object(s: str) -> str:
        """
        Extract first {...} JSON object from a string (handles accidental leading text).
        """
        s = PolicyGate._strip_code_fences(s)
        # Fast path
        if s.startswith("{") and s.endswith("}"):
            return s
        # Extract first balanced-ish object
        m = re.search(r"\{.*\}", s, flags=re.DOTALL)
        if not m:
            raise PolicyViolation("Output does not contain a JSON object")
        return m.group(0)

    @staticmethod
    def validate(raw_text: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise PolicyViolation("Empty model output")

        candidate = PolicyGate._extract_json_object(raw_text)

        try:
            obj = json.loads(candidate)
        except Exception as e:
            raise PolicyViolation(f"Output is not valid JSON: {e}")

        if not isinstance(obj, dict):
            raise PolicyViolation("JSON must be an object")

        # Required keys
        for k in PolicyGate.REQUIRED_KEYS:
            if k not in obj:
                raise PolicyViolation(f"Missing required key: {k}")

        # Type checks (minimal)
        if not isinstance(obj["explanation"], str):
            raise PolicyViolation("explanation must be a string")
        if not isinstance(obj["confidence_language"], dict):
            raise PolicyViolation("confidence_language must be an object")
        if not isinstance(obj["evidence_ids"], list):
            raise PolicyViolation("evidence_ids must be a list")
        if not isinstance(obj["what_would_change_my_mind"], list):
            raise PolicyViolation("what_would_change_my_mind must be a list")

        # IDs must be strings (or castable) — we enforce strings
        obj["evidence_ids"] = [str(x) for x in obj["evidence_ids"]]
        obj["what_would_change_my_mind"] = [str(x) for x in obj["what_would_change_my_mind"]]

        # Disallowed language scan over the whole raw output (not only JSON)
        low = raw_text.lower()
        for pat in PolicyGate.DISALLOWED_PATTERNS:
            if re.search(pat, low):
                raise PolicyViolation(f"Disallowed content detected by pattern: {pat}")

        return obj
