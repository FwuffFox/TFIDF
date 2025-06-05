from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uuid
import os
import hashlib
from app.db import get_session, engine
from app.db.models import Corpus, Document, Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI, session: AsyncSession = Depends(get_session)):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile, session: AsyncSession = Depends(get_session)):
    try:
        text: str = (await file.read()).decode('utf-8')
        if not text.strip():
            return {"error": "File is empty or contains only whitespace."}
        
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        existing = await session.execute(select(Document).where(Document.hash == text_hash))
        existing_doc = existing.scalar_one_or_none()
        if existing_doc:
            return RedirectResponse(url=f"/result/{existing_doc.id}", status_code=303)
        
        document_id = str(uuid.uuid4())
        doc = Document(id=document_id, text=text, hash=text_hash)
        session.add(doc)
        await session.commit()
        return RedirectResponse(url=f"/result/{document_id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

per_page = 50
@app.get("/result/{document_id}", response_class=HTMLResponse)
async def view_result(request: Request, document_id: str, page: int = 1, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        return {"error": "Document not found."}
    
    text = doc.text
    is_duplicate = hash(text) in tfidf_calculator.document_hashes
    tfidf_result = tfidf_calculator.calculate_tfidf(text)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_result = tfidf_result[start:end]
    total_pages = (len(tfidf_result) + per_page - 1) // per_page
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": paginated_result,
        "page": page,
        "total_pages": total_pages,
        "text": text,
        "is_duplicate": is_duplicate,
        "upload_count": tfidf_calculator.total_documents,
        "document_id": document_id
    })

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    return {"status": "ok"}

@app.get("/version", response_class=HTMLResponse)
async def version(request: Request):
    return {"version": f"{os.getenv('APP_VERSION', '1.0.0')}"}