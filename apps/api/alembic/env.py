"""Alembic migration environment — synchronous psycopg2 engine.

Uses psycopg2 (sync) for migrations to avoid the Windows asyncpg/OpenSSL
issue. The FastAPI runtime still uses asyncpg via SQLAlchemy async — this
only affects the alembic CLI.

The database URL is read from config.settings (.env.local), with the
asyncpg driver replaced by psycopg2 for the migration connection.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from config import settings

# Import all models so Alembic can discover the full schema for autogenerate
import models  # noqa: F401
from database import Base

alembic_cfg = context.config

# Convert async URL → sync: postgresql+asyncpg://... → postgresql+psycopg2://...
_sync_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql+asyncpg+ssl://", "postgresql+psycopg2://"
)
alembic_cfg.set_main_option("sqlalchemy.url", _sync_url)

if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database using psycopg2 (sync)."""
    connectable = create_engine(
        _sync_url,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
