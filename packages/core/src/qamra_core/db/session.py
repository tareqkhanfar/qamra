"""Engines and sessions. psycopg 3 serves both the async API and the sync worker/migrations."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


def make_async_engine(url: str, pool_size: int = 5) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True, pool_size=pool_size, max_overflow=pool_size)


def make_async_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def make_sync_engine(url: str, pool_size: int = 2) -> Engine:
    return create_engine(url, pool_pre_ping=True, pool_size=pool_size, max_overflow=pool_size)


def make_sync_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
