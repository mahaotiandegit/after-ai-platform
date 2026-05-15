from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def check_database() -> dict:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS ok"))
            value = result.scalar_one()
        return {
            "status": "ok",
            "detail": f"postgres connected, select_result={value}",
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }
