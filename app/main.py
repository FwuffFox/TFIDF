import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine, get_session
from app.db.models import Base
from app.valkey import valkey_instance as valkey

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI, session: AsyncSession = Depends(get_session)):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


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
    min_time = await valkey.get("min_processing_time")
    max_time = (await valkey.get("max_processing_time")) or 0
    average_time = (await valkey.get("average_processing_time")) or 0
    last_time = (await valkey.get("last_processing_time")) or 0
    latest_file_timestamp = (
        await valkey.get("latest_file_processed_timestamp")
    ) or "N/A"

    # Handle infinity case for JSON serialization
    if min_time is None or min_time == float("inf"):
        min_time = None

    return {
        "files_processed": files_processed,
        "min_processing_time": min_time,
        "max_processing_time": max_time,
        "average_processing_time": average_time,
        "last_processing_time": last_time,
        "latest_file_processed_timestamp": latest_file_timestamp,
    }
