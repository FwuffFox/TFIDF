import time

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, WordFrequency
from app.metrics import process_metrics
from app.tfidf import process_new_document


async def process_document(
    session: AsyncSession, corpus_id: str, filename: str, text: str
) -> Document:
    """
    Process the document text and return a Document object.
    """
    start = time.time()
    if not text.strip():
        raise ValueError("Document text cannot be empty or whitespace.")

    # Ensure the file is unique by checking its hash
    import hashlib

    text_hash = hashlib.sha256(f"{corpus_id}{text}".encode("utf-8")).hexdigest()
    result = await session.execute(select(Document).where(Document.hash == text_hash))

    if document := result.scalar_one_or_none():
        return document

    document = Document(
        filename=filename, text=text, hash=text_hash, corpus_id=corpus_id
    )

    session.add(document)
    await session.flush()  # Flush to get the document ID

    await process_new_document(session, document)

    await session.commit()

    await process_metrics(time.time() - start)

    return document


async def get_document(session: AsyncSession, document_id: str) -> Document | None:
    """
    Retrieve a Document object by its ID.
    """
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if document:
        print(f"Retrieved document: {document.id} - {document.filename}")

    return document


async def get_documents_by_corpus(
    session: AsyncSession, corpus_id: str, page: int = 1, per_page: int = 50
):
    """
    Retrieve a paginated list of Document objects by corpus ID.
    """
    offset = (page - 1) * per_page
    result = await session.execute(
        select(Document)
        .where(Document.corpus_id == corpus_id)
        .offset(offset)
        .limit(per_page)
    )

    documents = result.scalars().all()

    return documents


async def get_document_count(session: AsyncSession, corpus_id: str) -> int:
    """
    Get the total number of documents in a specific corpus.
    """
    result = await session.execute(
        select(func.count(distinct(Document.id))).where(Document.corpus_id == corpus_id)
    )

    return result.scalar_one()


async def get_document_and_word_frequencies(
    session: AsyncSession, document_id: str, page: int = 1, per_page: int = 50
) -> tuple[Document | None, list[WordFrequency]]:
    """
    Retrieve a Document and its associated WordFrequency records with pagination.
    """
    document = await get_document(session, document_id)

    if not document:
        print(f"Document with ID {document_id} not found.")
        return None, []

    offset = (page - 1) * per_page
    word_freq_result = await session.execute(
        select(WordFrequency)
        .where(WordFrequency.document_id == document_id)
        .offset(offset)
        .limit(per_page)
    )

    word_frequencies = list(word_freq_result.scalars().all())

    return document, word_frequencies
