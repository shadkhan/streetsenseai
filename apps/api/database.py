"""Async SQLAlchemy engine, session factory, and declarative Base.

All models inherit from Base. All route handlers and service functions
receive an AsyncSession via FastAPI dependency injection (get_db).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,   # recycles stale connections after docker restarts
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped AsyncSession per request."""
    async with async_session_factory() as session:
        yield session


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency — yields a Redis client, closed on teardown."""
    r: aioredis.Redis = aioredis.from_url(settings.redis_url)
    try:
        yield r
    finally:
        await r.aclose()
