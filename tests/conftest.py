import os
from typing import AsyncGenerator

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

data = {}


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_test_cache_storage() -> AsyncGenerator[MockRedisClient, None]:
    # Use our mock Redis client instead of a real client
    cache = MockRedisClient(data)
    try:
        yield cache
    finally:
        await cache.close()


@pytest.fixture(scope="module", autouse=True)
def override_deps():
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_cache_storage] = get_test_cache_storage


@pytest.fixture(scope="module")
async def client():
    """
    Create a test client for the FastAPI app.
    This will use the in-memory SQLite database for testing.
    """
    from fastapi.testclient import TestClient

    async with engine.begin() as conn:
        # Create all tables in the in-memory SQLite database
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
