def prosody_from_confidence(conf: float) -> dict:
    """
    Deterministic mapping confidence -> prosody controls.
    Prevents manipulative drift.
    """
    if conf >= 0.85:
        return {"stability": 0.70, "style": 0.25, "tone": "confident"}
    if conf >= 0.60:
        return {"stability": 0.80, "style": 0.20, "tone": "measured"}
    return {"stability": 0.90, "style": 0.10, "tone": "uncertain"}
