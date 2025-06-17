from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Collection


class CollectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, collection_id: str) -> Optional[Collection]:
        """
        Retrieve a collection by its ID.

        Args:
            collection_id (str): The ID of the collection to retrieve.

        Returns:
            Optional[Collection]: The Collection object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_documents(self, collection_id: str) -> Optional[Collection]:
        result = await self.session.execute(
            select(Collection).where(Collection.id == collection_id)
            .options(selectinload(Collection.documents))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Collection]:
        """
        Retrieve a collection by its name.
        Args:
            name (str): The name of the collection to retrieve.

        Returns:
            Optional[Collection]: The Collection object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Collection).where(Collection.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id, offset: int = 0, limit: int = 50
    ) -> Sequence[Collection]:
        """
        Retrieve collections associated with a specific user.

        Args:
            user_id (str): The ID of the user to filter collections by.
            offset (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.

        Returns:
            Sequence[Collection]: A sequence of Collection objects associated with the specified user.
        """
        result = await self.session.execute(
            select(Collection)
            .where(Collection.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(
        self, name: str, user_id: str, description: Optional[str] = None
    ) -> Collection:
        collection = Collection(name=name, user_id=user_id, description=description)
        self.session.add(collection)
        await self.session.commit()
        await self.session.refresh(collection)
        return collection

    async def delete(self, collection_id: str):
        collection = await self.get(collection_id)
        if collection:
            await self.session.delete(collection)
            await self.session.commit()
        return collection

    async def add_document(self, collection_id: str, document_id: str) -> bool:
        """
        Add a document to a collection.

        Args:
            collection_id (str): The ID of the collection to add the document to
            document_id (str): The ID of the document to add

        Returns:
            bool: True if document was added successfully, False otherwise
        """
        from app.db.models import Document

        # Get the collection
        collection = await self.get_with_documents(collection_id)
        if not collection:
            return False

        # Get the document
        document_query = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = document_query.scalar_one_or_none()
        if not document:
            return False

        # Check if document is already in the collection
        if document in collection.documents:
            return True  # Document is already in the collection

        # Add document to collection
        collection.documents.append(document)
        await self.session.commit()
        return True

    async def remove_document(self, collection_id: str, document_id: str) -> bool:
        """
        Remove a document from a collection.

        Args:
            collection_id (str): The ID of the collection to remove the document from
            document_id (str): The ID of the document to remove

        Returns:
            bool: True if document was removed successfully, False otherwise
        """
        from app.db.models import Document

        # Get the collection
        collection = await self.get_with_documents(collection_id)
        if not collection:
            return False

        # Get the document
        document_query = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = document_query.scalar_one_or_none()
        if not document:
            return False

        # Check if document is in the collection
        if document not in collection.documents:
            return True  # Document is already not in the collection

        # Remove document from collection
        collection.documents.remove(document)
        await self.session.commit()
        return True





