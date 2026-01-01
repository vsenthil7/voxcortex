# HealthCheck/03_ai_audit_check.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from services.shared.db import get_engine


def main():
    print("=== AI AUDIT CHECK ===")
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT trace_id, phase, model_name, policy_status, policy_error, created_at
                FROM ai_call_audit
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

    print("✅ AI AUDIT CHECK COMPLETE")


if __name__ == "__main__":
    main()
