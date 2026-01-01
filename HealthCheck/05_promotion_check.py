# HealthCheck/05_promotion_check.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from services.shared.db import get_engine


def main():
    print("=== PROMOTION CHECK ===")
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, trace_id, belief_id, hypothesis_id, decision, decision_reason, promoted_confidence, created_at
                FROM belief_promotions
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
        ).fetchall()

    if not rows:
        print("(no rows found)")
    else:
        for r in rows:
            print(r)

    print("✅ PROMOTION CHECK COMPLETE")


if __name__ == "__main__":
    main()
