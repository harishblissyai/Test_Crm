"""
Alembic async migration environment.

To add a new migration:
    cd backend
    alembic revision --autogenerate -m "your message"

To apply migrations:
    alembic upgrade head

To roll back one step:
    alembic downgrade -1
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Load app settings and Base ─────────────────────────────────
from app.core.config import settings
from app.db.session import Base

# Import all models here so Alembic can detect schema changes for autogenerate.
from app.models.user import RefreshToken, Tenant, User  # noqa: F401
from app.models.client import Client  # noqa: F401

# ── Alembic config ─────────────────────────────────────────────
alembic_cfg = context.config
alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

target_metadata = Base.metadata


# ── Offline migrations (no live DB connection) ─────────────────
def run_migrations_offline() -> None:
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations (async engine) ──────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
