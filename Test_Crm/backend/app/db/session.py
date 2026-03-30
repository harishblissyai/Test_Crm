"""
Database session factory.

Provides:
    engine          — shared async SQLAlchemy engine
    AsyncSessionLocal — session factory
    Base            — all models inherit from this
    get_db()        — FastAPI dependency that yields a session per request
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ─────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # logs SQL in DEBUG mode
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # verify connections before use
)

# ── Session factory ────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # keep objects usable after commit
)

# ── Declarative base ───────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this class."""
    pass


# ── FastAPI dependency ─────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    Yields an AsyncSession per request.
    Auto-commits on success, auto-rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
