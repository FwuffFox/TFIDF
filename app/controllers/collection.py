from fastapi import APIRouter, Depends, HTTPException, Path

from app.controllers.utils.responses import response401, response403, response404
from app.dependencies import get_corpus_repository
from app.repositories.corpus import CorpusRepository
from app.utils.auth import AuthenticatedUser

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get(
    "/",
    summary="List collections",
    description="Retrieves all document collections belonging to the authenticated user.",
    responses={
        200: {
            "description": "List of user's collections",
            "content": {
                "application/json": {
                    "example": [
                        {"id": "col1", "name": "Research Papers"},
                        {"id": "col2", "name": "Technical Documentation"}
                    ]
                }
            },
        },
        401: response401,
    },
)
async def list_collections(
    user: AuthenticatedUser, repo: CorpusRepository = Depends(get_corpus_repository)
):
    """
    List all collections belonging to the authenticated user.
    
    Args:
        user (AuthenticatedUser): The authenticated user.
        repo (CorpusRepository): Repository for corpus operations.
        
    Returns:
        list: A list of collections with their IDs and names.
    """
    collections = await repo.get_all(user.id)
    return [{"id": c.id, "name": c.name} for c in collections]


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
                            {"id": "doc2", "filename": "transformers.txt"}
                        ]
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
    collection_id: str = Path(..., description="The ID of the collection to retrieve"),
    repo: CorpusRepository = Depends(get_corpus_repository),
):
    """
    Get detailed information about a specific collection.
    
    This endpoint retrieves a collection by its ID, including the list of documents
    that belong to the collection. The collection must belong to the requesting user.
    
    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection to retrieve.
        repo (CorpusRepository): Repository for corpus operations.
        
    Returns:
        dict: Detailed collection information including documents.
        
    Raises:
        HTTPException: If collection not found (404) or access denied (403).
    """
    collection = await repo.get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if collection.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at.isoformat(),
        "documents": [
            {"id": doc.id, "filename": doc.filename} for doc in collection.documents
        ],
    }


@router.post(
    "/{collection_id}/{document_id}",
    summary="Add document to collection",
    description="Adds an existing document to a collection. Both must belong to the authenticated user.",
    responses={
        200: {
            "description": "Document successfully added to collection",
            "content": {
                "application/json": {
                    "example": {"status": "added"}
                }
            },
        },
        403: response403,
        404: response404,
    },
)
async def add_document_to_collection(
    user: AuthenticatedUser,
    collection_id: str = Path(..., description="The ID of the collection"),
    document_id: str = Path(..., description="The ID of the document to add"),
    repo: CorpusRepository = Depends(get_corpus_repository),
):
    """
    Add a document to a collection.
    
    This endpoint associates an existing document with a collection.
    Both the document and collection must belong to the requesting user.
    
    Args:
        user (AuthenticatedUser): The authenticated user.
        collection_id (str): The ID of the collection.
        document_id (str): The ID of the document to add.
        repo (CorpusRepository): Repository for corpus operations.
        
    Returns:
        dict: A status message indicating the document was added.
        
    Raises:
        HTTPException: If collection or document not found (404) or access denied (403).
    """
    # TODO: реализовать добавление документа в коллекцию
    return {"status": "added"}


@router.delete(
    "/{collection_id}/{document_id}",
    summary="Remove document from collection",
    description="Removes a document from a collection. The document itself is not deleted.",
    responses={
        200: {
            "description": "Document successfully removed from collection",
            "content": {
                "application/json": {
                    "example": {"status": "removed"}
                }
            },
        },
        403: response403,
        404: response404,
    },
)
async def remove_document_from_collection(
    user: AuthenticatedUser,
    collection_id: str = Path(..., description="The ID of the collection"),
    document_id: str = Path(..., description="The ID of the document to remove"),
    repo: CorpusRepository = Depends(get_corpus_repository),
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
        repo (CorpusRepository): Repository for corpus operations.
        
    Returns:
        dict: A status message indicating the document was removed.
        
    Raises:
        HTTPException: If collection or document not found (404) or access denied (403).
    """
    # TODO: реализовать удаление документа из коллекции
    return {"status": "removed"}
