"""
Shared pytest fixtures — uses a real PostgreSQL test database.

Database : blissycrm_test
Strategy : NullPool engine (no connection sharing between tasks),
           table truncation between tests for isolation.

Run once before tests: docker-compose up -d
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop — required for session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:password@localhost:5432/blissycrm_test"
)

# NullPool: every connect() creates a fresh connection — avoids asyncpg
# "attached to a different loop" errors when connections are used across tasks.
_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
_session_factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)



@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables once for the entire test session, drop at the end."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables(setup_database):
    """Truncate all tables BEFORE each test so tests start with a clean slate."""
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(
                text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            )


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Direct DB session for test setup (e.g. seeding users)."""
    async with _session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_database):
    """
    AsyncClient wired to the test app.
    Each HTTP request gets its own fresh DB session (via NullPool).
    """
    app = create_app()

    async def override_get_db():
        async with _session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
