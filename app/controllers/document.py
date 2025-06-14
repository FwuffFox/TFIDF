import asyncio
import logging
from io import BytesIO
from typing import Dict, List, Optional

from fastapi import (APIRouter, Depends, File, HTTPException, Path, Query,
                     UploadFile)
from fastapi.responses import JSONResponse, StreamingResponse

from app.controllers.utils.responses import (response401, response403,
                                             response404)
from app.dependencies import (get_document_repository, get_storage_service,
                              get_tfidf_service)
from app.repositories.document import DocumentRepository
from app.services.tfidf_service import TFIDFService
from app.utils import hash_file_md5
from app.utils.auth import AuthenticatedUser
from app.utils.storage import FileStorage

logger = logging.getLogger(__name__)

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
    logger.info(f"Document upload requested - Title: {title}, User: {user.username}")

    filebytes = await file.read()
    file_hash = hash_file_md5(user.id, filebytes)

    # Check if document with same hash already exists
    if await doc_repo.get_by_hash(file_hash):
        logger.warning(
            f"Document upload failed - Duplicate content, Title: {title}, User: {user.username}"
        )
        raise HTTPException(
            status_code=400, detail="Document with same content already exists"
        )

    # Create document record
    document = await doc_repo.create(user.id, title, file_hash)
    logger.info(
        f"Document record created - ID: {document.id}, Title: {title}, User: {user.username}"
    )

    # Save file to storage
    location = str(
        await storage.save_bytes_by_path(filebytes, f"{user.id}/{document.id}")
    )
    logger.debug(f"Document file saved - ID: {document.id}, Location: {location}")

    # Update document with file location
    await doc_repo.update_location(document.id, location)
    logger.debug(f"Document location updated - ID: {document.id}")

    # Process document text to extract word frequencies and term frequencies
    async def process_document_task():
        try:
            logger.info(
                f"Starting background processing of document text - ID: {document.id}"
            )
            success = await doc_repo.process_document_text(
                document.id, filebytes.decode("utf-8", errors="ignore")
            )
            if success:
                logger.info(
                    f"Document text processing completed successfully - ID: {document.id}"
                )
            else:
                logger.warning(f"Document text processing failed - ID: {document.id}")
        except Exception as e:
            logger.error(
                f"Error during document text processing - ID: {document.id}: {str(e)}",
                exc_info=True,
            )

    # Execute document processing in background
    asyncio.create_task(process_document_task())
    logger.info(f"Document processing task initiated - ID: {document.id}")

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
    file_content = await storage.get_file_by_path(document.location)

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
    status_code=202,
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
    logger.info(
        f"Document deletion requested - ID: {document_id}, User: {user.username}"
    )

    document = await repo.get(document_id)
    if not document:
        logger.warning(
            f"Document deletion failed - Document not found, ID: {document_id}, User: {user.username}"
        )
        raise HTTPException(status_code=404, detail="Resource not found")

    if document.user_id != user.id:
        logger.warning(
            f"Document deletion failed - Access denied, ID: {document_id}, User: {user.username}, Owner: {document.user_id}"
        )
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(
        f"Document deletion authorized - ID: {document_id}, Title: {document.title}, User: {user.username}"
    )

    async def delete_document_task():
        try:
            # Delete file from storage if it exists
            tasks = []
            if document.location:
                logger.debug(f"Deleting document file - Location: {document.location}")
                tasks.append(storage.delete_file_by_path(str(document.location)))

            # Delete database record
            logger.debug(f"Deleting document record from database - ID: {document_id}")
            tasks.append(repo.delete(document_id))

            await asyncio.gather(*tasks)
            logger.info(
                f"Document deletion completed successfully - ID: {document_id}, Title: {document.title}, User: {user.username}"
            )
        except Exception as e:
            logger.error(
                f"Error during background deletion of document {document_id}: {str(e)}",
                exc_info=True,
            )

    # Create background task and return immediately
    asyncio.create_task(delete_document_task())
    logger.info(
        f"Document deletion task initiated - ID: {document_id}, User: {user.username}"
    )

    return {"status": "deletion_in_progress"}


@router.get(
    "/{document_id}/statistics",
    response_model=List[Dict],
    summary="Get document word statistics",
    description="Retrieves word frequency statistics and TF-IDF analysis for a specific document, optionally in the context of a collection.",
    responses={
        200: {
            "description": "List of words with their frequencies and TF-IDF scores",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "word": "example",
                            "frequency": 5,
                            "tf": 0.8333,
                            "idf": 1.6931,
                            "tfidf": 1.4109,
                        },
                        {
                            "word": "document",
                            "frequency": 3,
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
async def get_document_statistics(
    user: AuthenticatedUser,
    document_id: str = Path(
        ..., description="The ID of the document to get statistics for"
    ),
    collection_id: Optional[str] = Query(
        None,
        description="Optional collection ID to provide collection context for TF-IDF calculation",
    ),
    repo: DocumentRepository = Depends(get_document_repository),
    tfidf_service: TFIDFService = Depends(get_tfidf_service),
):
    """
    Retrieve word frequency statistics and TF-IDF analysis for a specific document.

    This endpoint returns the frequency of each word in the document along with
    TF-IDF scores to identify important words. The document must belong to the requesting user.
    When a collection ID is provided, the TF-IDF calculation uses the collection context.

    Args:
        user (AuthenticatedUser): The authenticated user.
        document_id (str): ID of the document to analyze.
        collection_id (Optional[str]): Optional collection ID to provide collection context.
        repo (DocumentRepository): Document repository dependency.
        tfidf_service (TFIDFService): TFIDF calculation service dependency.

    Returns:
        List[Dict]: List of words with their frequencies and TF-IDF scores.

    Raises:
        HTTPException: If document not found (404) or access denied (403).
    """
    logger.info(
        f"Document statistics requested - ID: {document_id}, User: {user.username}, Collection: {collection_id}"
    )

    document = await repo.get(document_id)
    if not document:
        logger.warning(
            f"Document statistics request failed - Document not found, ID: {document_id}, User: {user.username}"
        )
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != user.id:
        logger.warning(
            f"Document statistics request failed - Access denied, ID: {document_id}, User: {user.username}, Owner: {document.user_id}"
        )
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(
        f"Retrieving word frequencies for document - ID: {document_id}, Title: {document.title}"
    )

    try:
        # Calculate TF-IDF scores
        logger.info(
            f"Calculating TF-IDF scores for document - ID: {document_id}, Collection: {collection_id}"
        )
        tfidf_results = await tfidf_service.calculate_tfidf_for_document(
            document_id, collection_id
        )

        logger.info(
            f"TF-IDF analysis completed for document - ID: {document_id}, Found {len(tfidf_results)} terms"
        )
        return tfidf_results
    except Exception as e:
        logger.error(
            f"Error retrieving statistics for document {document_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve document statistics"
        )
