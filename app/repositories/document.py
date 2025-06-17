import logging
import math
import time
from typing import Dict, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Collection, Document, WordFrequency
from app.utils.metrics import MetricsService

logger = logging.getLogger(__name__)


class DocumentRepository:
    def __init__(self, session: AsyncSession, metrics: MetricsService):
        self.session = session
        self.metrics = metrics

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

    async def get_with_collections(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID.

        Args:
            document_id (str): The ID of the document to retrieve.

        Returns:
            Optional[Document]: The Document object if found, otherwise None.
        """
        result = await self.session.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.collections))
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

    async def get_by_collection(
        self, collection_id: str, offset: int = 0, limit: int = 50
    ) -> Sequence[Document]:
        """
        Retrieve documents associated with a specific collection.

        Args:
            collection_id (str): The ID of the collection to filter documents by.
            offset (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.

        Returns:
            Sequence[Document]: A sequence of Document objects associated with the specified corpus.
        """
        result = await self.session.execute(
            select(Document)
            .join(Document.collections)
            .where(Document.collections.any(id=collection_id))
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
            file_hash (str): The hash value of the document content.

        Returns:
            Document: The created Document object.
        """
        document = Document(user_id=user_id, title=title, hash=file_hash)
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def delete(self, document_id: str) -> Optional[Document]:
        """
        Delete a document by its ID.

        Args:
            document_id (str): The ID of the document to delete.

        Returns:
            Optional[Document]: The deleted Document object if found, otherwise None.
        """
        document = await self.get(document_id)
        if document:
            await self.session.delete(document)
            await self.session.commit()
            return document
        return None

    async def add_word_frequencies(
        self, document_id: str, word_counts: Dict[str, int]
    ) -> None:
        """
        Add word frequencies to a document and calculate TF scores.

        Args:
            document_id (str): The ID of the document to add frequencies to.
            word_counts (Dict[str, int]): Dictionary mapping words to their counts in the document.
        """
        # Calculate total words for TF calculation
        total_words = sum(word_counts.values())

        # Create and add WordFrequency objects for each word
        word_frequencies = []
        for word, count in word_counts.items():
            # Calculate TF as word count / total words in document
            tf_score = count / total_words if total_words > 0 else 0

            word_freq = WordFrequency(
                word=word, frequency=count, tf_score=tf_score, document_id=document_id
            )
            word_frequencies.append(word_freq)

        self.session.add_all(word_frequencies)
        await self.session.commit()

    async def calculate_document_frequency(
        self, user_id: str, collection_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Calculate document frequency (number of documents containing each word).
        If collection_id is provided, only documents in that collection are considered.
        Otherwise, all documents from the user are considered.

        Args:
            user_id (str): The ID of the user.
            collection_id (Optional[str]): The ID of the collection for scoping.
                                           If None, all user documents are considered.

        Returns:
            Dict[str, int]: Dictionary mapping words to their document frequencies.
        """
        query = select(
            WordFrequency.word,
            func.count(func.distinct(WordFrequency.document_id)).label("doc_count"),
        )

        # Join with Document to filter by user_id
        query = query.join(Document, WordFrequency.document_id == Document.id)
        query = query.where(Document.user_id == user_id)

        # Apply collection filter if provided
        if collection_id:
            subquery = (
                select(Document.id)
                .join(Document.collections)
                .where(Collection.id == collection_id)
            )
            query = query.where(
                WordFrequency.document_id.in_(subquery.scalar_subquery())
            )

        query = query.group_by(WordFrequency.word)
        result = await self.session.execute(query)

        return {row.word: row.doc_count for row in result}

    async def calculate_total_documents(
        self, user_id: str, collection_id: Optional[str] = None
    ) -> int:
        """
        Calculate total number of documents for a user, optionally filtered by collection.

        Args:
            user_id (str): The ID of the user.
            collection_id (Optional[str]): The ID of the collection for scoping.
                                           If None, all user documents are counted.

        Returns:
            int: Total number of documents in the specified scope.
        """
        query = select(func.count(Document.id))
        query = query.where(Document.user_id == user_id)

        if collection_id:
            # Count documents in a specific collection
            query = query.join(Document.collections).where(
                Collection.id == collection_id
            )

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def calculate_tfidf(
        self, document_id: str, user_id: str, collection_id: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate TF-IDF scores for a document.
        If collection_id is provided, only documents in that collection are considered for IDF.
        Otherwise, all documents from the user are considered.

        Args:
            document_id (str): The ID of the document to calculate TF-IDF for.
            user_id (str): The ID of the user who owns the document.
            collection_id (Optional[str]): The ID of the collection for scoping.
                                         If None, all user documents are considered.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping words to their statistics including:
                - frequency: Raw word count in the document
                - tf: Term Frequency score
                - df: Document Frequency (number of documents containing the word)
                - idf: Inverse Document Frequency score
                - tfidf: TF-IDF score
        """
        start_time = time.time()
        
        # Get document word frequencies with TF scores
        query = select(WordFrequency).where(WordFrequency.document_id == document_id)
        result = await self.session.execute(query)
        word_frequencies = result.scalars().all()

        # Calculate document frequencies
        doc_frequencies = await self.calculate_document_frequency(
            user_id, collection_id
        )

        # Get total document count
        total_docs = await self.calculate_total_documents(user_id, collection_id)

        # Calculate statistics for each word
        word_stats = {}
        for wf in word_frequencies:
            # Get document frequency (df) for this word, default to 1 to avoid division by zero
            df = doc_frequencies.get(wf.word, 1)

            # Calculate IDF: log(total_docs / df)
            idf = math.log(total_docs / df) if df > 0 else 0

            # Calculate TF-IDF
            tfidf = wf.tf_score * idf

            # Store all statistics
            word_stats[wf.word] = {
                "frequency": wf.frequency,
                "tf": wf.tf_score,
                "df": df,
                "idf": idf,
                "tfidf": tfidf,
            }
        end_time = time.time()
        logger.debug(
            f"Calculated TF-IDF for document {document_id} in {end_time - start_time:.2f} seconds"
        )
        await self.metrics.file_processed(end_time - start_time)
        return word_stats

    async def update_location(self, document_id: str, location: str) -> None:
        """
        Update the file location for a document.

        Args:
            document_id (str): The ID of the document to update.
            location (str): The file location to set.
        """
        document = await self.get(document_id)
        if document:
            document.location = location
            await self.session.commit()

    async def process_document_text(self, document_id: str, text: str) -> bool:
        """
        Process document text to extract word frequencies and calculate term frequencies.

        Args:
            document_id (str): The ID of the document to process.
            text (str): The document text to process.

        Returns:
            bool: True if processing was successful, False otherwise.
        """
        try:
            # Get the document to ensure it exists
            document = await self.get(document_id)
            if not document:
                logger.error(f"Document not found for processing: {document_id}")
                return False

            # Import here to avoid circular imports
            from app.utils.text_processing import extract_word_frequencies

            # Extract word frequencies from text
            word_counts = extract_word_frequencies(text)

            # Add word frequencies to the document
            await self.add_word_frequencies(document_id, word_counts)

            return True
        except Exception as e:
            logger.error(f"Error processing document text: {str(e)}", exc_info=True)
            return False
