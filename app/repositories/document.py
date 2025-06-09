from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, WordFrequency


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, document_id: str):
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, corpus_id: str, offset: int = 0, limit: int = 50):
        result = await self.session.execute(
            select(Document)
            .where(Document.corpus_id == corpus_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all_from_user(self, user_id: str, offset: int = 0, limit: int = 50):
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, document: Document):
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def delete(self, document_id: str):
        document = await self.get(document_id)
        if document:
            await self.session.delete(document)
            await self.session.commit()
        return document
    
    async def get_statistics(self, document_id: str) -> Sequence[WordFrequency]:
        """
        Retrieve word frequency statistics for a specific document.
        """
        result = await self.session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document_id)
        )
        return result.scalars().all()