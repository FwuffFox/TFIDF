import os
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from valkey.asyncio import Redis

from app.db import async_session
from app.repositories.collection import CollectionRepository
from app.repositories.document import DocumentRepository
from app.repositories.user import UserRepository
from app.utils.storage import FileStorage
from app.utils.token_manager import TokenManager

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_user_repository(session: AsyncSession = Depends(get_async_session)):
    return UserRepository(session)


def get_document_repository(session: AsyncSession = Depends(get_async_session)):
    return DocumentRepository(session)


def get_collection_repository(session: AsyncSession = Depends(get_async_session)):
    return CollectionRepository(session)


def get_storage_service():
    return FileStorage(os.getenv("STORAGE_FOLDER"))


async def get_cache_storage() -> AsyncGenerator[Redis, None]:
    from app.utils.cache import cache_storage

    async with cache_storage as cache_storage:
        yield cache_storage


def get_token_manager(cache_storage=Depends(get_cache_storage)):
    """
    Provides a token manager instance for handling token operations.
    """

    return TokenManager(cache_storage)


UserRepository = Annotated[UserRepository, Depends(get_user_repository)]
DocumentRepository = Annotated[DocumentRepository, Depends(get_document_repository)]
CollectionRepository = Annotated[CollectionRepository, Depends(get_collection_repository)]
FileStorage = Annotated[FileStorage, Depends(get_storage_service)]
CacheStorage = Annotated[Redis, Depends(get_storage_service)]
TokenManager = Annotated[TokenManager, Depends(get_storage_service)]
