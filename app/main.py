from contextlib import asynccontextmanager
import bcrypt
from fastapi import FastAPI, Request, UploadFile, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uuid
import os
import hashlib
from app.db import get_session, engine
from app.db.models import Corpus, Document, Base, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.document import process_document, get_document_and_word_frequencies

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