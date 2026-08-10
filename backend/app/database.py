"""
Database configuration for IPO Copilot AI.

Supports both SQLite (development) and PostgreSQL (production).
Connection pooling is configured per database type:
  - SQLite: WAL mode, busy timeout, no pool (StaticPool)
  - PostgreSQL: QueuePool with 10 connections, overflow 20
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, text, NullPool

from app.config import settings

_IS_SQLITE = "sqlite" in settings.DATABASE_URL
_IS_POSTGRES = "postgresql" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL

# ── Engine configuration ─────────────────────────────────────────────────────
_engine_kwargs: dict = {
    "echo": False,
}

if _IS_SQLITE:
    # SQLite: no connection pooling (single file); use StaticPool for in-process dev
    _engine_kwargs["connect_args"] = {"timeout": 30.0}
elif _IS_POSTGRES:
    # PostgreSQL: production-grade pooling
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_timeout"] = 30
    _engine_kwargs["pool_recycle"] = 1800   # recycle connections every 30 min
    _engine_kwargs["pool_pre_ping"] = True   # validate connections before use

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable SQLite WAL mode and tuning — no-op for PostgreSQL."""
    if _IS_SQLITE:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Alias used by background tasks (fire-and-forget jobs that manage their own sessions)
async_session_factory = AsyncSessionLocal

Base = declarative_base()


async def get_db():
    """FastAPI dependency: yields a database session with automatic commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables from SQLAlchemy metadata (development / first-boot only).
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_database_connection() -> bool:
    """Verify that the database is reachable. Used by /health endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
