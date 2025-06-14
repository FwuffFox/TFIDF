import logging
import math
from typing import Dict, List, Set

from app.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)


class TFIDFService:
    """
    Service for calculating TF-IDF (Term Frequency-Inverse Document Frequency) values.

    This service provides methods to analyze the importance of words in documents
    relative to a collection of documents.
    """

    def __init__(self, document_repository: DocumentRepository):
        """
        Initialize the TFIDF service with a document repository.

        Args:
            document_repository: Repository for accessing document data
        """
        self.document_repository = document_repository

    async def calculate_tfidf_for_document(
        self, document_id: str, collection_id: str = None
    ) -> List[Dict]:
        """
        Calculate TF-IDF scores for all words in a specific document.

        Args:
            document_id: ID of the document to analyze
            collection_id: Optional collection ID to limit the document collection for IDF calculation
                       If None, all documents from the same user will be considered

        Returns:
            List of dictionaries with word, frequency, and tfidf score
        """
        logger.info(
            f"Calculating TF-IDF for document ID: {document_id}, collection ID: {collection_id}"
        )

        try:
            # Get the target document
            document = await self.document_repository.get(document_id)
            if not document:
                logger.warning(f"Document not found: {document_id}")
                return []

            # Get word frequencies for this document (TF part)
            word_frequencies = await self.document_repository.get_word_frequencies(
                document_id
            )
            if not word_frequencies:
                logger.warning(f"No word frequencies found for document: {document_id}")
                return []

            # Get all documents for IDF calculation
            if collection_id:
                all_documents = await self.document_repository.get_by_collection(
                    collection_id
                )
                logger.info(
                    f"Using {len(all_documents)} documents from collection {collection_id} for IDF calculation"
                )
            else:
                all_documents = await self.document_repository.get_by_user(
                    document.user_id
                )
                logger.info(
                    f"Using {len(all_documents)} documents from user {document.user_id} for IDF calculation"
                )

            # Calculate IDF for each word
            total_docs = len(all_documents)
            document_ids = [doc.id for doc in all_documents]

            # Get words and their document frequencies
            word_to_doc_count = await self._calculate_document_frequencies(
                document_ids, {wf.word for wf in word_frequencies}
            )

            # Calculate TF-IDF scores
            results = []
            max_frequency = (
                max([wf.frequency for wf in word_frequencies])
                if word_frequencies
                else 1
            )

            for wf in word_frequencies:
                # Term frequency (normalized by max frequency in document)
                tf = wf.frequency / max_frequency

                # Inverse document frequency
                doc_count = word_to_doc_count.get(wf.word, 0)
                # Add 1 to doc_count to avoid division by zero
                idf = math.log((total_docs + 1) / (doc_count + 1)) + 1

                # TF-IDF score
                tfidf = tf * idf

                results.append(
                    {
                        "word": wf.word,
                        "frequency": wf.frequency,
                        "tf": round(tf, 4),
                        "idf": round(idf, 4),
                        "tfidf": round(tfidf, 4),
                    }
                )

            # Sort by TF-IDF score descending
            results.sort(key=lambda x: x["tfidf"], reverse=True)
            logger.info(
                f"Successfully calculated TF-IDF for document {document_id}, found {len(results)} terms"
            )

            return results

        except Exception as e:
            logger.error(
                f"Error calculating TF-IDF for document {document_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def _calculate_document_frequencies(
        self, document_ids: List[str], target_words: Set[str]
    ) -> Dict[str, int]:
        """
        Calculate how many documents contain each word.

        Args:
            document_ids: List of document IDs to analyze
            target_words: Set of words to consider

        Returns:
            Dictionary mapping each word to the number of documents containing it
        """
        word_to_doc_count = {word: 0 for word in target_words}

        # Fetch word frequencies for all documents
        for doc_id in document_ids:
            try:
                word_freqs = await self.document_repository.get_word_frequencies(doc_id)
                doc_words = {wf.word for wf in word_freqs}

                # Update counts for target words that appear in this document
                for word in target_words:
                    if word in doc_words:
                        word_to_doc_count[word] += 1
            except Exception as e:
                logger.warning(
                    f"Error processing document {doc_id} for word frequencies: {str(e)}"
                )
                continue

        return word_to_doc_count
