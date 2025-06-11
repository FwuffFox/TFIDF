import asyncio
from io import BytesIO
from typing import Dict, List

from fastapi import (APIRouter, Depends, File, HTTPException, Path, Query,
                     UploadFile)
from fastapi.responses import StreamingResponse

from app.controllers.utils.responses import (response401, response403,
                                             response404)
from app.dependencies import get_document_repository, get_storage_service
from app.repositories.document import DocumentRepository
from app.utils import hash_file_md5
from app.utils.auth import AuthenticatedUser
from app.utils.storage import FileStorage

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "/",
    response_model=List[Dict[str, str]],
    summary="List user documents",
    description="Retrieves a paginated list of all documents belonging to the authenticated user.",
    responses={
        200: {
            "description": "A list of documents with their IDs and titles",
            "content": {
                "application/json": {
                    "example": [
                        {"id": "doc1", "title": "Document 1"},
                        {"id": "doc2", "title": "Document 2"},
                    ]
                }
            },
        },
        401: response401,
        403: response403,
    },
)
async def list_documents(
    user: AuthenticatedUser,
    doc_repo: DocumentRepository = Depends(get_document_repository),
    offset: int = Query(
        0, description="Number of documents to skip for pagination", ge=0
    ),
    limit: int = Query(
        100, description="Maximum number of documents to return", ge=1, le=500
    ),
) -> List[Dict[str, str]]:
    """
    List documents for the authenticated user.

    Args:
        user (AuthenticatedUser): The authenticated user.
        doc_repo (DocumentRepository): Dependency to access the document repository.
        offset (int): The number of records to skip (for pagination).
        limit (int): The maximum number of records to return.

    Returns:
        List[Dict[str, str]]: A list of documents with their IDs and titles.
    """
    documents = await doc_repo.get_by_user(user.id, offset=offset, limit=limit)
    return [{"id": d.id, "title": d.title} for d in documents]


@router.post(
    "/",
    status_code=201,
    summary="Upload a new document",
    description="Uploads a new document file and associates it with the authenticated user.",
    response_description="Returns a success status with the document ID",
    responses={
        201: {
            "description": "Document successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "status": "created",
                        "id": "doc1",
                        "title": "Document 1",
                    }
                }
            },
        },
        400: {
            "description": "Document with same content already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Document with same content already exists"}
                }
            },
        },
    },
)
async def create_document(
    user: AuthenticatedUser,
    title: str = Query(..., description="The title of the document"),
    file: UploadFile = File(..., description="The document file to upload"),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    storage: FileStorage = Depends(get_storage_service),
):
    """
    Upload a new document file.

    This endpoint allows users to upload document files which are then stored
    in the system. The API prevents duplicate uploads by comparing file hashes.

    Args:
        user: The authenticated user
        title: Title of the document
        file: Document file to upload
        doc_repo: Document repository dependency
        storage: Storage service dependency

    Returns:
        Dict containing status and document details

    Raises:
        HTTPException: If document with same content already exists (400)
    """
    filebytes = await file.read()
    file_hash = hash_file_md5(user.id, filebytes)
    if await doc_repo.get_by_hash(file_hash):
        raise HTTPException(
            status_code=400, detail="Document with same content already exists"
        )

    document = await doc_repo.create(user.id, title, file_hash)

    location = await storage.save_bytes(filebytes, document.id, user.id)

    await doc_repo.update_location(document.id, location)

    return {"status": "created", "id": document.id, "title": document.title}


@router.get(
    "/{document_id}",
    response_class=StreamingResponse,
    summary="Download document",
    description="Downloads a specific document by its ID. The document is returned as a file attachment.",
    responses={
        200: {
            "description": "The document file",
            "content": {"application/octet-stream": {}},
        },
        403: response403,
        404: response404,
    },
)
async def get_document(
    user: AuthenticatedUser,
    document_id: str = Path(..., description="The ID of the document to retrieve"),
    repo: DocumentRepository = Depends(get_document_repository),
    storage: FileStorage = Depends(get_storage_service),
) -> StreamingResponse:
    """
    Retrieve a specific document by its ID for the authenticated user.

    This endpoint retrieves the document file and returns it as a downloadable
    attachment. The document must belong to the requesting user.

    Args:
        user: The authenticated user
        document_id: ID of the document to retrieve
        repo: Document repository dependency
        storage: Storage service dependency

    Returns:
        StreamingResponse containing the document file

    Raises:
        HTTPException: If document not found (404), access denied (403), or file missing (404)
    """
    document = await repo.get(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get file content from storage
    file_content = await storage.get_file(document.location)

    # Check if file was found
    if file_content is None:
        raise HTTPException(
            status_code=404,
            detail="Document file not found in storage. The file may have been deleted or moved.",
        )

    # return as a file
    file_stream = BytesIO(file_content)
    return StreamingResponse(
        file_stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={document.title}.txt"},
    )


@router.delete(
    "/{document_id}",
    summary="Delete document",
    description="Deletes a specific document by its ID. The document must belong to the authenticated user.",
    responses={
        202: {
            "description": "Document deletion accepted",
            "content": {
                "application/json": {"example": {"status": "deletion_in_progress"}}
            },
        },
        403: response403,
        404: response404,
    },
)
async def delete_document(
    user: AuthenticatedUser,
    document_id: str = Path(..., description="The ID of the document to delete"),
    repo: DocumentRepository = Depends(get_document_repository),
    storage: FileStorage = Depends(get_storage_service),
):
    """
    Delete a specific document by its ID.

    This endpoint deletes both the database record and the associated file.
    The document must belong to the requesting user.

    Args:
        user: The authenticated user
        document_id: ID of the document to delete
        repo: Document repository dependency
        storage: Storage service dependency for deleting the file

    Returns:
        Dict with deletion status

    Raises:
        HTTPException: If document not found (404) or access denied (403)
    """
    document = await repo.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resource not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    async def delete_document_task():
        try:
            # Delete file from storage if it exists
            tasks = []
            if document.location:
                tasks.append(storage.delete_file(document.location))  # type: ignore

            # Delete database record
            tasks.append(repo.delete(document_id))

            await asyncio.gather(*tasks)
        except Exception as e:
            print(
                f"Error during background deletion of document {document_id}: {str(e)}"
            )

    # Create background task and return immediately
    asyncio.create_task(delete_document_task())

    return {"status": "deletion_in_progress"}


@router.get(
    "/{document_id}/statistics",
    response_model=List[Dict[str, str]],
    summary="Get document word statistics",
    description="Retrieves word frequency statistics for a specific document.",
    responses={
        200: {
            "description": "List of word frequencies",
            "content": {
                "application/json": {
                    "example": [
                        {"word": "example", "frequency": 5},
                        {"word": "document", "frequency": 3},
                    ]
                }
            },
        },
        403: response403,
        404: response404,
    },
)
async def get_document_statistics(
    user: AuthenticatedUser,
    document_id: str = Path(
        ..., description="The ID of the document to get statistics for"
    ),
    repo: DocumentRepository = Depends(get_document_repository),
):
    """
    Retrieve word frequency statistics for a specific document.

    This endpoint returns the frequency of each word in the document.
    The document must belong to the requesting user.

    Args:
        user: The authenticated user
        document_id: ID of the document to get statistics for
        repo: Document repository dependency

    Returns:
        List of dictionaries containing word and frequency information

    Raises:
        HTTPException: If document not found (404) or access denied (403)
    """
    document = await repo.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resource not found")

    if document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    statistics = await repo.get_statistics(document_id)
    return [{"word": stat.word, "frequency": stat.frequency} for stat in statistics]
