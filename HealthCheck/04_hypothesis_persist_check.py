# HealthCheck/04_hypothesis_persist_check.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from services.shared.db import get_engine


def main():
    print("=== HYPOTHESIS PERSIST CHECK ===")
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, trace_id, belief_id, ai_call_audit_id, hypothesis, confidence, evidence_ids, created_at
                FROM hypotheses
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
        ).fetchall()

    if not rows:
        print("(no rows found yet)")
    else:
        for r in rows:
            print(r)

    print("✅ HYPOTHESIS PERSIST CHECK COMPLETE")


if __name__ == "__main__":
    main()
