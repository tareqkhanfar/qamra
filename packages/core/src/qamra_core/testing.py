"""Pytest plugin shared by core, api and worker tests (`pytest_plugins = ["qamra_core.testing"]`).

Database tests need TEST_DATABASE_URL. Each session rebuilds the schema through the Alembic
migrations (so migrations are tested too); each test runs in a transaction that is rolled back.
"""

import os
from collections.abc import AsyncIterator, Iterator

import boto3
import pytest
from botocore.client import Config
from moto import mock_aws
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from qamra_core.migrations import upgrade
from qamra_core.storage import ObjectStorage

TEST_BUCKET = "qamra-test"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL is not set (see .env.example; `docker compose up postgres` works)")
    if not url.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
        pytest.fail("refusing to run: TEST_DATABASE_URL must point at a database whose name ends in _test")
    return url


@pytest.fixture(scope="session")
def migrated(database_url: str) -> str:
    engine = create_engine(database_url, poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    upgrade(database_url)
    return database_url


@pytest.fixture(scope="session")
def sync_engine(migrated: str) -> Iterator[Engine]:
    engine = create_engine(migrated, pool_size=1, max_overflow=0)
    yield engine
    engine.dispose()


@pytest.fixture
def db(sync_engine: Engine) -> Iterator[Session]:
    """Sync session inside a rolled-back transaction; `commit()` only releases a savepoint."""
    with sync_engine.connect() as conn:
        trans = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            session.close()
            trans.rollback()


@pytest.fixture(scope="session")
async def async_engine(migrated: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated, pool_size=1, max_overflow=0)
    yield engine
    await engine.dispose()


@pytest.fixture
async def adb(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
def storage() -> Iterator[ObjectStorage]:
    """In-memory S3 (moto)."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version="s3v4"))
        client.create_bucket(Bucket=TEST_BUCKET)
        yield ObjectStorage(client=client, bucket=TEST_BUCKET, sse="AES256", default_ttl=600)
