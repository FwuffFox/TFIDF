import logging
import math
from typing import Annotated, Dict, List

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.controllers.utils.responses import (response401, response403,
                                             response404)
from app.dependencies import CollectionRepository, DocumentRepository
from app.services.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["collections"])


class CreateCollectionDTO(BaseModel):
    name: str
    description: str = None


@router.get(
    "/",
    summary="List collections",
    response_model=None,
    responses={
        200: {
            "description": "List of user's collections",
            "content": {
                "application/json": {
                    "example": [
                        {"id": "col1", "name": "Research Papers"},
                        {"id": "col2", "name": "Technical Documentation"},
                    ]
                }
            },
        },
        401: response401,
    },
)
async def list_collections(
    user: AuthenticatedUser,
    collection_repo: CollectionRepository,
):
    """
    List all collections belonging to the authenticated user.

    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_repo (CollectionRepository): Repository for collection operations.

    Returns:
        list: A list of collections with their IDs and names.
    """
    logger.info(f"Listing collections for user: {user.username}")

    try:
        collections = await collection_repo.get_by_user(user.id)
        collection_count = len(collections)
        logger.info(
            f"Retrieved {collection_count} collections for user: {user.username}"
        )
        return [{"id": c.id, "name": c.name} for c in collections]
    except Exception as e:
        logger.error(
            f"Error retrieving collections for user {user.username}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve collections")


@router.post(
    "/",
    summary="Create a new collection",
    description="Creates a new collection.",
    status_code=201,
    responses={
        201: {
            "description": "Collection created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "col1",
                        "name": "New Collection",
                        "description": "Description of the new collection",
                        "created_at": "2025-05-12T10:30:00",
                    }
                }
            },
        },
        403: response403,
    },
)
async def create_collection(
    user: AuthenticatedUser,
    collection_data: CreateCollectionDTO,
    collection_repo: CollectionRepository,
):
    logger.info(f"Creating collection: {collection_data.name}")
    try:
        collection = await collection_repo.create(
            collection_data.name, user.id, collection_data.description
        )
        logger.info(f"Collection created successfully: {collection.id}")

        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(
            f"Error creating collection: {collection_data.name}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to create collection")


@router.get(
    "/{collection_id}",
    summary="Get collection details",
    description="Retrieves detailed information about a specific collection, including its documents.",
    responses={
        200: {
            "description": "Collection details with document list",
            "content": {
                "application/json": {
                    "example": {
                        "id": "col1",
                        "name": "Research Papers",
                        "description": "Academic research papers on NLP",
                        "created_at": "2025-05-12T10:30:00",
                        "documents": [
                            {"id": "doc1", "filename": "nlp_research.txt"},
                            {"id": "doc2", "filename": "transformers.txt"},
                        ],
                    }
                }
            },
        },
        403: response403,
        404: response404,
    },
)
async def get_collection(
    user: AuthenticatedUser,
    collection_id: Annotated[
        str, Path(description="The ID of the collection to retrieve")
    ],
    repo: CollectionRepository,
):
    """
    Get detailed information about a specific collection.

    This endpoint retrieves a collection by its ID, including the list of documents
    that belong to the collection. The collection must belong to the requesting user.

    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection to retrieve.
        repo (CollectionRepository): Repository for collection operations.

    Returns:
        dict: Detailed collection information including documents.

    Raises:
        HTTPException: If collection not found (404) or access denied (403).
    """
    logger.info(
        f"Collection details requested - ID: {collection_id}, User: {user.username}"
    )

    try:
        collection = await repo.get_with_documents(collection_id)
        if not collection:
            logger.warning(
                f"Collection details request failed - Collection not found, ID: {collection_id}, User: {user.username}"
            )
            raise HTTPException(status_code=404, detail="Collection not found")

        if collection.user_id != user.id:
            logger.warning(
                f"Collection details request failed - Access denied, ID: {collection_id}, User: {user.username}, Owner: {collection.user_id}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        document_count = len(collection.documents) if collection.documents else 0
        logger.info(
            f"Collection details retrieved - ID: {collection_id}, Name: {collection.name}, Documents: {document_count}, User: {user.username}"
        )

        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
            "documents": [
                {"id": doc.id, "title": doc.title} for doc in collection.documents
            ],
        }
    except HTTPException:
        # Re-raise HTTP exceptions since they've already been logged
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving collection details for ID {collection_id}, User {user.username}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve collection details"
        )


@router.post(
    "/{collection_id}/{document_id}",
    summary="Add document to collection",
    description="Adds an existing document to a collection. Both must belong to the authenticated user.",
    responses={
        200: {
            "description": "Document successfully added to collection",
            "content": {"application/json": {"example": {"status": "added"}}},
        },
        403: response403,
        404: response404,
    },
)
async def add_document_to_collection(
    user: AuthenticatedUser,
    collection_id: Annotated[str, Path(..., description="The ID of the collection")],
    document_id: Annotated[str, Path(..., description="The ID of the document to add")],
    collection_repo: CollectionRepository,
    doc_repo: DocumentRepository,
):
    """
    Add a document to a collection.

    This endpoint associates an existing document with a collection.
    Both the document and collection must belong to the requesting user.

    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection.
        document_id (str): The ID of the document to add.
        collection_repo (CollectionRepository): Repository for collection operations.
        doc_repo (DocumentRepository): Repository for document operations.

    Returns:
        dict: A status message indicating the document was added.

    Raises:
        HTTPException: If collection or document not found (404) or access denied (403).
    """
    logger.info(
        f"Add document to collection requested - Collection: {collection_id}, Document: {document_id}, User: {user.username}"
    )

    try:
        # Check if collection exists and belongs to the user
        collection = await collection_repo.get(collection_id)
        if not collection:
            logger.warning(f"Collection not found, ID: {collection_id}")
            raise HTTPException(status_code=404, detail="Collection not found")

        if collection.user_id != user.id:
            logger.warning(
                f"Access to collection denied, ID: {collection_id}, User: {user.username}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if document exists and belongs to the user
        document = await doc_repo.get(document_id)
        if not document:
            logger.warning(f"Document not found, ID: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        if document.user_id != user.id:
            logger.warning(
                f"Access to document denied, ID: {document_id}, User: {user.username}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        # Add document to collection
        result = await collection_repo.add_document(collection_id, document_id)
        if not result:
            logger.error(
                f"Failed to add document to collection - Collection: {collection_id}, Document: {document_id}"
            )
            raise HTTPException(
                status_code=500, detail="Failed to add document to collection"
            )

        logger.info(
            f"Document added to collection successfully - Collection: {collection_id}, Document: {document_id}, User: {user.username}"
        )
        return {"status": "added"}
    except HTTPException:
        # Re-raise HTTP exceptions since they've already been logged
        raise
    except Exception as e:
        logger.error(
            f"Error adding document {document_id} to collection {collection_id} for user {user.username}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to add document to collection"
        )


@router.delete(
    "/{collection_id}/{document_id}",
    summary="Remove document from collection",
    description="Removes a document from a collection. The document itself is not deleted.",
    responses={
        200: {
            "description": "Document successfully removed from collection",
            "content": {"application/json": {"example": {"status": "removed"}}},
        },
        403: response403,
        404: response404,
    },
)
async def remove_document_from_collection(
    user: AuthenticatedUser,
    collection_id: Annotated[str, Path(..., description="The ID of the collection")],
    document_id: Annotated[
        str, Path(..., description="The ID of the document to remove")
    ],
    collection_repo: CollectionRepository,
    doc_repo: DocumentRepository,
):
    """
    Remove a document from a collection.

    This endpoint removes the association between a document and a collection.
    Both the document and collection must belong to the requesting user.
    The document itself is not deleted, only removed from the collection.

    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection.
        document_id (str): The ID of the document to remove.
        collection_repo (CollectionRepository): Repository for collection operations.
        doc_repo (DocumentRepository): Repository for document operations.

    Returns:
        dict: A status message indicating the document was removed.

    Raises:
        HTTPException: If collection or document not found (404) or access denied (403).
    """
    logger.info(
        f"Remove document from collection requested - Collection: {collection_id}, Document: {document_id}, User: {user.username}"
    )

    try:
        # Check if collection exists and belongs to the user
        collection = await collection_repo.get(collection_id)
        if not collection:
            logger.warning(f"Collection not found, ID: {collection_id}")
            raise HTTPException(status_code=404, detail="Collection not found")

        if collection.user_id != user.id:
            logger.warning(
                f"Access to collection denied, ID: {collection_id}, User: {user.username}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if document exists and belongs to the user
        document = await doc_repo.get(document_id)
        if not document:
            logger.warning(f"Document not found, ID: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        if document.user_id != user.id:
            logger.warning(
                f"Access to document denied, ID: {document_id}, User: {user.username}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        # Remove document from collection
        result = await collection_repo.remove_document(collection_id, document_id)
        if not result:
            logger.error(
                f"Failed to remove document from collection - Collection: {collection_id}, Document: {document_id}"
            )
            raise HTTPException(
                status_code=500, detail="Failed to remove document from collection"
            )

        logger.info(
            f"Document removed from collection successfully - Collection: {collection_id}, Document: {document_id}, User: {user.username}"
        )
        return {"status": "removed"}
    except HTTPException:
        # Re-raise HTTP exceptions since they've already been logged
        raise
    except Exception as e:
        logger.error(
            f"Error removing document {document_id} from collection {collection_id} for user {user.username}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to remove document from collection"
        )


@router.get(
    "/{collection_id}/statistics",
    response_model=List[Dict],
    summary="Get collection statistics",
    description="Retrieves word statistics for all documents in a collection, treating them as a single document for TF calculation.",
    responses={
        200: {
            "description": "List of words with their frequencies, TF, IDF, and TF-IDF scores",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "word": "example",
                            "frequency": 10,
                            "tf": 0.8333,
                            "idf": 1.6931,
                            "tfidf": 1.4109,
                        },
                        {
                            "word": "document",
                            "frequency": 6,
                            "tf": 0.5,
                            "idf": 1.0986,
                            "tfidf": 0.5493,
                        },
                    ]
                }
            },
        },
        403: response403,
        404: response404,
    },
)
async def get_collection_statistics(
    user: AuthenticatedUser,
    collection_id: Annotated[
        str, Path(description="The ID of the collection to analyze")
    ],
    collection_repo: CollectionRepository,
    doc_repo: DocumentRepository,
):
    """
    Retrieve word statistics for all documents in a collection.

    This endpoint calculates word frequencies and TF-IDF scores for a collection,
    treating all documents in the collection as if they were a single document
    for Term Frequency (TF) calculation, while keeping the standard IDF calculation.

    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection to analyze.
        collection_repo (CollectionRepository): Repository for collection operations.
        doc_repo (DocumentRepository): Repository for document operations.

    Returns:
        List[Dict]: List of words with their combined frequencies and TF-IDF scores.

    Raises:
        HTTPException: If collection not found (404) or access denied (403).
    """
    logger.info(
        f"Collection statistics requested - ID: {collection_id}, User: {user.username}"
    )

    try:
        # Check if collection exists and belongs to the user
        collection = await collection_repo.get_with_documents(collection_id)
        if not collection:
            logger.warning(f"Collection not found, ID: {collection_id}")
            raise HTTPException(status_code=404, detail="Collection not found")

        if collection.user_id != user.id:
            logger.warning(
                f"Access to collection denied, ID: {collection_id}, User: {user.username}"
            )
            raise HTTPException(status_code=403, detail="Access denied")

        # Get all documents in the collection
        documents = collection.documents
        if not documents:
            logger.info(f"Collection has no documents, ID: {collection_id}")
            return []

        # Get document frequencies across all documents in the collection
        doc_frequencies = await doc_repo.calculate_document_frequency(
            user.id, collection_id
        )
        
        # Get total document count in the collection
        total_docs = await doc_repo.calculate_total_documents(user.id, collection_id)
        
        # Combine word frequencies from all documents into a single count
        combined_word_counts = {}
        for doc in documents:
            # Fetch word frequencies for this document
            
            word_frequencies = await doc_repo.get_word_frequencies(doc.id)
            
            # Add frequencies to the combined counts
            for wf in word_frequencies:
                if wf.word in combined_word_counts:
                    combined_word_counts[wf.word] += wf.frequency
                else:
                    combined_word_counts[wf.word] = wf.frequency
        
        # Calculate total words across all documents for TF calculation
        total_words = sum(combined_word_counts.values())
        
        # Calculate statistics for each word
        word_stats = []
        for word, frequency in combined_word_counts.items():
            # Calculate TF for the combined collection (frequency / total words)
            tf = frequency / total_words if total_words > 0 else 0
            
            # Get document frequency (df) for this word, default to 1 to avoid division by zero
            df = doc_frequencies.get(word, 1)
            
            # Calculate IDF: log(total_docs / df)
            idf = math.log(total_docs / df) if df > 0 else 0
            
            # Calculate TF-IDF
            tfidf = tf * idf
            
            # Add to results
            word_stats.append({
                "word": word,
                "frequency": frequency,
                "tf": round(tf, 4),
                "idf": round(idf, 4),
                "tfidf": round(tfidf, 4)
            })
        
        # Sort by TF-IDF score in descending order
        word_stats.sort(key=lambda x: x["tfidf"], reverse=True)
        
        logger.info(
            f"Collection statistics calculated successfully - ID: {collection_id}, Words: {len(word_stats)}"
        )
        return word_stats[:50]
        
    except HTTPException:
        # Re-raise HTTP exceptions since they've already been logged
        raise
    except Exception as e:
        logger.error(
            f"Error calculating collection statistics for ID {collection_id}, User {user.username}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to calculate collection statistics"
        )
