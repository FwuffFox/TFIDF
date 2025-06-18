import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request

from app.controllers.collection import router as collection_router
from app.controllers.document import router as document_router
from app.controllers.metrics import router as metrics_router
from app.controllers.user import router as user_router
from app.db import engine
from app.db.models import Base
from app.dependencies import get_cache_storage

load_dotenv()


# Configure logging
def configure_logging():
    """
    Configure the logging system for the application.
    Sets up console and file handlers with appropriate formatting.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create a formatter for our logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers to avoid duplicate logs
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler - log to a file
    log_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(f"{log_dir}/app.log")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Set specific logger levels if needed
    # For example, you might want to reduce noise from some modules
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.info("Logging configured successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging at application startup
    configure_logging()
    logging.info("Application starting up")

    # Create database tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        logging.info("Database tables created or verified")

    yield

    logging.info("Application shutting down")


app = FastAPI(
    lifespan=lifespan,
    title="Document Management API + TF-IDF",
    description="API for managing documents, collections, and users with TF-IDF support.",
    version=os.getenv("API_VERSION", "1.0"),
)

# Include routers for controllers
app.include_router(collection_router)
app.include_router(document_router)
app.include_router(user_router)
app.include_router(metrics_router)


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
