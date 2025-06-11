import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.controllers.collection import router as collection_router
from app.controllers.document import router as document_router
from app.controllers.user import router as user_router
from app.db import engine
from app.db.models import Base
from app.dependencies import get_cache_storage

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

# Include routers for controllers
app.include_router(collection_router)
app.include_router(document_router)
app.include_router(user_router)


@app.get("/")
async def index(request: Request):
    if os.getenv("ENV") == "development":
        from starlette.responses import RedirectResponse

        return RedirectResponse(url="/docs")
    return None


@app.get("/status")
async def status(request: Request):
    return {"status": "ok"}


@app.get("/version")
async def version(request: Request):
    return {"version": f"{os.getenv('APP_VERSION', '1.0.0')}"}


@app.get("/metrics")
async def metrics(request: Request, cache=Depends(get_cache_storage)):
    files_processed = (await cache.get("files_processed")) or 0
    min_time = await cache.get("min_processing_time")
    max_time = (await cache.get("max_processing_time")) or 0
    average_time = (await cache.get("average_processing_time")) or 0
    last_time = (await cache.get("last_processing_time")) or 0
    latest_file_timestamp = (
        await cache.get("latest_file_processed_timestamp")
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
