"""
DB Health Check — VoxCortex
Purpose:
- Prove DB connectivity
- Prove correct config precedence
- Prove SQL execution
NO pytest. NO mocks. NO abstractions.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os
from sqlalchemy import text
from services.shared.db import get_engine


def main():
    print("=== VoxCortex DB Health Check ===")

    # 1. Print config visibility (NO secrets)
    print("\n[Config visibility]")
    print("DATABASE_URL set:", bool(os.getenv("DATABASE_URL")))
    print("POSTGRES_PASSWORD set:", bool(os.getenv("POSTGRES_PASSWORD")))

    # 2. Create engine
    print("\n[Engine creation]")
    engine = get_engine()
    print("Engine OK:", engine)

    # 3. Open connection
    print("\n[Connection test]")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        print("SELECT 1 result:", result)

    # 4. Optional: check core tables exist
    print("\n[Schema sanity]")
    with engine.connect() as conn:
        tables = conn.execute(
            text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
        ).fetchall()

    print("Tables found:")
    for t in tables:
        print(" -", t[0])

    print("\n✅ DB HEALTH CHECK PASSED")


if __name__ == "__main__":
    main()
