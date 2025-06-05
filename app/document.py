from app.db.models import Document
from app.db import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tfidf import process_new_document

async def process_document(session: AsyncSession, corpus_id: str, filename: str, text: str) -> Document:
    """
    Process the document text and return a Document object.
    """
    if not text.strip():
        raise ValueError("Document text cannot be empty or whitespace.")
    
    # Ensure the file is unique by checking its hash
    import hashlib
    text_hash = hashlib.sha256(f"{corpus_id}{text}".encode('utf-8')).hexdigest()
    result = await session.execute(select(Document).where(Document.hash == text_hash))

    if document := result.scalar_one_or_none():
        return document

    document = Document(
        filename=filename,
        text=text,
        hash=text_hash,
        corpus_id=corpus_id
    )

    session.add(document)

    await process_new_document(session, document)

    await session.commit()

    return document
