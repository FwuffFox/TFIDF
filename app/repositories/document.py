from typing import Sequence, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, WordFrequency


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID.
        
        Args:
            document_id (str): The ID of the document to retrieve.
            
        Returns:
            Optional[Document]: The Document object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, hash_value: str) -> Optional[Document]:
        """
        Retrieve a document by its hash value.
        
        Args:
            hash_value (str): The hash value of the document to retrieve.
            
        Returns:
            Optional[Document]: The Document object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Document).where(Document.hash == hash_value)
        )
        return result.scalar_one_or_none()

    async def get_by_corpus(self, corpus_id: str, offset: int = 0, limit: int = 50) -> Sequence[Document]:
        """
        Retrieve documents associated with a specific corpus.
        
        Args:
            corpus_id (str): The ID of the corpus to filter documents by.
            offset (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.
            
        Returns:
            Sequence[Document]: A sequence of Document objects associated with the specified corpus.
        """
        result = await self.session.execute(
            select(Document)
            .join(Document.corpuses)
            .where(Document.corpuses.any(id=corpus_id))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_user(self, user_id: str, offset: int = 0, limit: int = 50) -> Sequence[Document]:
        """
        Retrieve documents associated with a specific user.
        
        Args:
            user_id (str): The ID of the user to filter documents by.
            offset (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.
            
        Returns:
            Sequence[Document]: A sequence of Document objects associated with the specified user.
        """
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, user_id: str, title: str, file_hash: str) -> Document:
        """
        Create a new document with the given user ID, title, and hash.
        
        Args:
            user_id (str): The ID of the user creating the document.
            title (str): The title of the document.
            hash (str): The hash value of the document content.
            
        Returns:
            Document: The created Document object.
        """
        document = Document(user_id=user_id, title=title, hash=file_hash)
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
