from typing import AsyncGenerator

import pytest

import os

from sqlalchemy import WithinGroup

from app.main import app
from app.dependencies import get_session

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

# in memory sqlite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.db.models import Base

async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

@pytest.fixture(scope="module")
async def client():
    """
    Create a test client for the FastAPI app.
    This will use the in-memory SQLite database for testing.
    """
    from fastapi.testclient import TestClient
    app.dependency_overrides[get_session] = get_test_session
    async with engine.begin() as conn:
        # Create all tables in the in-memory SQLite database
        await conn.run_sync(Base.metadata.create_all)
    return TestClient(app)
