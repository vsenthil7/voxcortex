import os
from sqlalchemy import create_engine
from services.shared.config import Settings

_ENGINE = None


def get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    # -------------------------------------------------
    # 1. Cloud / CI / prod override
    # -------------------------------------------------
    db_url = os.getenv("DATABASE_URL")

    # -------------------------------------------------
    # 2. config.py (your existing fix)
    # -------------------------------------------------
    if not db_url:
        settings = Settings()
        db_url = settings.database_url

    # -------------------------------------------------
    # 3. Local dev fallback (MATCHES psql behaviour)
    # -------------------------------------------------
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "voxcortex")

        if not password:
            raise RuntimeError(
                "No database credentials found.\n"
                "Checked: DATABASE_URL, config.py, POSTGRES_PASSWORD"
            )

        db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    _ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        future=True,
    )

    return _ENGINE
