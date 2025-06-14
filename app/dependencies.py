import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_user_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.user import UserRepository

    return UserRepository(session)


def get_document_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.document import DocumentRepository

    return DocumentRepository(session)


def get_collection_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.collection import CollectionRepository

    return CollectionRepository(session)


def get_tfidf_service(doc_repo=Depends(get_document_repository)):
    from app.services.tfidf_service import TFIDFService

    return TFIDFService(doc_repo)


def get_storage_service():
    from app.utils.storage import FileStorage

    return FileStorage(os.getenv("STORAGE_FOLDER"))


@asynccontextmanager
async def get_cache_storage():
    from app.utils.cache import cache_storage

    async with cache_storage as cache_storage:
        yield cache_storage


def get_token_manager(cache_storage=Depends(get_cache_storage)):
    """
    Provides a token manager instance for handling token operations.
    """

    from app.utils.token_manager import TokenManager

    return TokenManager(cache_storage)
