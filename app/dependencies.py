import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


def get_user_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.user import UserRepository

    return UserRepository(session)


def get_document_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.document import DocumentRepository

    return DocumentRepository(session)


def get_corpus_repository(session: AsyncSession = Depends(get_session)):
    from app.repositories.corpus import CorpusRepository

    return CorpusRepository(session)


def get_storage_service():
    from app.utils.storage import FileStorage

    return FileStorage(os.getenv("STORAGE_FOLDER"))
