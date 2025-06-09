from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_document_repository
from app.repositories.document import DocumentRepository
from app.utils.auth import AuthenticatedUser

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
async def list_documents(
    user: AuthenticatedUser,
    doc_repo: DocumentRepository = Depends(get_document_repository),
    offset: int = 0,
    limit: int = 100,
) -> list[dict[str, str]]:
    """
    List documents for the authenticated user.
    
    Args:
        user (AuthenticatedUser): The authenticated user.
        doc_repo (DocumentRepository): Dependency to access the document repository.
        offset (int): The number of records to skip (for pagination).
        limit (int): The maximum number of records to return.
        
    Returns:
        List[Dict[str, str]]: A list of documents with their IDs and filenames.
    """
    documents = await doc_repo.get_by_user(user.id, offset=offset, limit=limit)
    return [{"id": d.id, "filename": d.filename} for d in documents]


@router.get("/{document_id}")
async def get_document(
    user: AuthenticatedUser,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repository),
):
    """
    Retrieve a specific document by its ID for the authenticated user.
    
    Args:
        user (AuthenticatedUser): The authenticated user.
        document_id (str): The ID of the document to retrieve.
        repo (DocumentRepository): Dependency to access the document repository.
        
    Returns:
        Dict[str, str]: A dictionary containing the document's ID, filename, and text.
    """
    document = await repo.get(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"id": document.id, "filename": document.filename, "text": document.text}


@router.delete("/{document_id}")
async def delete_document(
    user: AuthenticatedUser,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repository),
):
    document = await repo.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await repo.delete(document_id)
    return {"status": "deleted"}


@router.get("/{document_id}/statistics")
async def get_document_statistics(
    user: AuthenticatedUser,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repository),
):
    document = await repo.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    statistics = await repo.get_statistics(document_id)
    return [{"word": stat.word, "frequency": stat.frequency} for stat in statistics]
