from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_document_repository
from app.repositories.document import DocumentRepository
from app.utils.auth import AuthenticatedUser

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
async def list_documents(
    user: AuthenticatedUser,
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    documents = await doc_repo.get_all_from_user(user.id)
    return [{"id": d.id, "filename": d.filename} for d in documents]


@router.get("/{document_id}")
async def get_document(
    user: AuthenticatedUser,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repository),
):
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
