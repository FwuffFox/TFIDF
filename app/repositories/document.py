import logging
import re
from io import BytesIO
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, WordFrequency
from app.utils.storage import FileStorage

logger = logging.getLogger(__name__)


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

    async def get_by_corpus(
        self, corpus_id: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Document]:
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

    async def get_by_user(
        self, user_id: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Document]:
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
        """
        Delete a document by its ID. Does not delete the file itself.
        Args:
            document_id (str): The ID of the document to delete.
        """
        document = await self.get(document_id)
        if document:
            await self.session.delete(document)
            await self.session.commit()
        return document

    async def update_location(
        self, document_id: str, location: str
    ) -> Optional[Document]:
        """
        Update the file location for a document.

        Args:
            document_id (str): The ID of the document to update.
            location (str): The file location to set.

        Returns:
            Optional[Document]: The updated Document object if found, otherwise None.
        """
        document = await self.get(document_id)
        if not document:
            return None

        document.location = location
        self.session.add(document)
        await self.session.commit()
        return document

    async def process_document_text(self, document_id: str, text: str) -> bool:
        """
        Process the document text to extract word frequencies and calculate term frequencies.

        Args:
            document_id: ID of the document to process
            text: Text content to process

        Returns:
            bool: True if processing was successful, False otherwise
        """
        logger.info(
            f"Processing document text for word frequencies - ID: {document_id}"
        )

        document = await self.get(document_id)
        if not document:
            logger.warning(
                f"Cannot process document - Document not found: {document_id}"
            )
            return False

        try:
            # Process text to count word frequencies
            word_counts = self._count_words(text)

            if not word_counts:
                logger.warning(f"No words found in document - ID: {document_id}")
                return False

            # Calculate term frequencies
            max_frequency = max(word_counts.values())

            # Store word frequencies and term frequencies in database
            word_frequencies = []
            for word, frequency in word_counts.items():
                # Calculate term frequency (normalized by max frequency)
                tf = frequency / max_frequency

                word_freq = WordFrequency(
                    word=word, frequency=frequency, tf_score=tf, document_id=document_id
                )
                word_frequencies.append(word_freq)

            # Add all word frequencies to database
            self.session.add_all(word_frequencies)
            await self.session.commit()

            logger.info(
                f"Successfully processed document - ID: {document_id}, Words: {len(word_frequencies)}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error processing document text - ID: {document_id}: {str(e)}",
                exc_info=True,
            )
            return False

    def _count_words(self, text: str) -> Dict[str, int]:
        """
        Count word frequencies in the document text.

        Args:
            text: Document text content

        Returns:
            Dict mapping words to their frequencies
        """
        # Convert to lowercase and split by non-alphanumeric characters
        words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())

        # Count word frequencies
        word_counts = {}
        for word in words:
            if len(word) > 1:  # Skip single-character words
                word_counts[word] = word_counts.get(word, 0) + 1

        return word_counts

    async def get_word_frequencies(self, document_id: str) -> Sequence[WordFrequency]:
        """
        Get word frequencies for a specific document.

        Args:
            document_id: ID of the document

        Returns:
            Sequence of WordFrequency objects
        """
        result = await self.session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document_id)
        )
        return result.scalars().all()
