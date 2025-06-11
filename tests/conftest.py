import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import WithinGroup
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.dependencies import get_session
from app.main import app
# in memory sqlite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.db.models import Base


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
        
@pytest.fixture(scope="module", autouse=True)
def override_session():
    """
    Override the default session dependency to use the in-memory SQLite database for testing.
    This fixture is automatically applied to all tests in the module.
    """
    app.dependency_overrides[get_session] = get_test_session
    
def get_cache_storage():
    """
    Provides a mock cache storage for testing purposes.
    This can be replaced with a real cache service in production.
    """
    from app.utils.valkey import valkey_instance
    return valkey_instance

@pytest.fixture(scope="module", autouse=True)
def override_cache_storage():
    """
    Override the cache storage dependency to use a mock cache for testing.
    This fixture is automatically applied to all tests in the module.
    """
    app.dependency_overrides[get_cache_storage] = get_cache_storage

def get_cache_storage():
    """
    Provides a mock cache storage for testing purposes.
    This can be replaced with a real cache service in production.
    """
    from app.utils.valkey import valkey_instance
    return valkey_instance

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac