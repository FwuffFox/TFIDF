import os
from typing import AsyncGenerator, Dict

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.dependencies import get_cache_storage, get_session, get_token_manager
from app.main import app
from tests.mock_redis import MockRedisClient

# in memory sqlite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.db.models import Base

# Global dictionary that will be reset for each test
_test_cache_data = {}


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
        # Rollback any changes to keep tests isolated
        await session.rollback()


async def get_test_cache_storage() -> AsyncGenerator[MockRedisClient, None]:
    # Use our mock Redis client with the global dictionary that's reset for each test
    global _test_cache_data
    cache = MockRedisClient(_test_cache_data)
    try:
        yield cache
    finally:
        await cache.close()


@pytest.fixture(scope="function", autouse=True)
def reset_test_data():
    """
    Reset the test cache data before each test.
    """
    global _test_cache_data
    _test_cache_data.clear()
    return _test_cache_data


@pytest.fixture(scope="function", autouse=True)
def override_deps():
    """
    Override app dependencies for testing.
    Using function scope ensures each test gets fresh dependencies.
    """
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_cache_storage] = get_test_cache_storage

    yield

    # Clean up after test
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client():
    """
    Create a test client for the FastAPI app.
    This will use the in-memory SQLite database for testing.
    Each test gets a fresh database with all tables created.
    """
    # Create all tables in the in-memory SQLite database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    # Drop all tables after the test to ensure a clean state
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
