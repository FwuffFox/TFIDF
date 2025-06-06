import os
from contextlib import asynccontextmanager

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine, get_session
from app.db.models import Base, Corpus, User
from app.document import get_document_and_word_frequencies, process_document
from app.valkey import valkey_instance as valkey

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
        
        name = file.filename
        if not name:
            return {"error": "File name is required."}
        
        user = (await session.execute(select(User).where(User.username == "default"))).scalar_one_or_none()
        if not user:
            user = User(username="default", password=str(bcrypt.hashpw(b"default", bcrypt.gensalt())), email="")
            session.add(user)
            await session.commit()

        corpus = (await session.execute(select(Corpus).where(Corpus.name == "default"))).scalar_one_or_none()
        if not corpus:
            corpus = Corpus(name="default", user_id=user.id)
            session.add(corpus)
            await session.commit()
        
        # corpus_id = request.query_params.get("corpus_id", corpus.id)

        document = await process_document(session, corpus.id, name, text)

        return RedirectResponse(url=f"/result/{document.id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/result/{document_id}")
async def view_result(request: Request, document_id: str, page: int = 1, session: AsyncSession = Depends(get_session)):
    document, word_freq = await get_document_and_word_frequencies(session, document_id)

    if not document:
        return {"error": "Document not found."}
    
    return {
        "document": document,
        "word_frequencies": word_freq,
    }

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/status")
async def status(request: Request):
    return {"status": "ok"}

@app.get("/version")
async def version(request: Request):
    return {"version": f"{os.getenv('APP_VERSION', '1.0.0')}"}

@app.get("/metrics")
async def metrics(request: Request):
    files_processed = (await valkey.get("files_processed")) or 0
    min_time = (await valkey.get("min_processing_time"))
    max_time = (await valkey.get("max_processing_time")) or 0
    average_time = (await valkey.get("average_processing_time")) or 0
    last_time = (await valkey.get("last_processing_time")) or 0
    latest_file_timestamp = (await valkey.get("latest_file_processed_timestamp")) or "N/A"

    # Handle infinity case for JSON serialization
    if min_time is None or min_time == float('inf'):
        min_time = None

    return {
        "files_processed": files_processed,
        "min_processing_time": min_time,
        "max_processing_time": max_time,
        "average_processing_time": average_time,
        "last_processing_time": last_time,
        "latest_file_processed_timestamp": latest_file_timestamp
    }