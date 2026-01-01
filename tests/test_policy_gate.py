# tests/test_policy_gate.py
import pytest
from services.policy.policy_gate import PolicyGate, PolicyViolation


def test_accepts_plain_json():
    raw = '{"explanation":"x","confidence_language":{"level":"low","calibration":"ok"},"evidence_ids":["1"],"what_would_change_my_mind":["y"]}'
    out = PolicyGate.validate(raw)
    assert out["explanation"] == "x"


def test_accepts_fenced_json():
    raw = """```json
{"explanation":"x","confidence_language":{"level":"low","calibration":"ok"},"evidence_ids":["1"],"what_would_change_my_mind":["y"]}
```"""
    out = PolicyGate.validate(raw)
    assert out["evidence_ids"] == ["1"]


def test_rejects_missing_key():
    raw = '{"explanation":"x","confidence_language":{},"evidence_ids":["1"]}'
    with pytest.raises(PolicyViolation):
        PolicyGate.validate(raw)


def test_rejects_action_language():
    raw = '{"explanation":"run psql","confidence_language":{"level":"low","calibration":"ok"},"evidence_ids":["1"],"what_would_change_my_mind":["y"]}'
    with pytest.raises(PolicyViolation):
        PolicyGate.validate(raw)
