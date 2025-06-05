from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost/tfidf')

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
