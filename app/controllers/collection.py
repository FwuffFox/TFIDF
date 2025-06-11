from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_corpus_repository
from app.repositories.corpus import CorpusRepository
from app.utils.auth import AuthenticatedUser

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/")
async def list_collections(
    user: AuthenticatedUser, repo: CorpusRepository = Depends(get_corpus_repository)
):
    collections = await repo.get_all(user.id)
    return [{"id": c.id, "name": c.name} for c in collections]


@router.get("/{collection_id}")
async def get_collection(
    user: AuthenticatedUser,
    collection_id: str,
    repo: CorpusRepository = Depends(get_corpus_repository),
):
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


@router.post("/{collection_id}/{document_id}")
async def add_document_to_collection(collection_id: str, document_id: str):
    # TODO: реализовать добавление документа в коллекцию
    return {"status": "added"}


@router.delete("/{collection_id}/{document_id}")
async def remove_document_from_collection(collection_id: str, document_id: str):
    # TODO: реализовать удаление документа из коллекции
    return {"status": "removed"}
