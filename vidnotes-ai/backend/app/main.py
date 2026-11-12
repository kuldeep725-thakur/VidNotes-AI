import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.todos import router as todos_router
from app.api.users import router as users_router
from app.api.videos import router as videos_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.database import init_db
from app.schemas.user import PublicConfig
from app.services.video_service import fail_interrupted_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("vidnotes")
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    fail_interrupted_jobs()
    if not settings.gemini_api_key or not settings.supadata_api_key:
        logger.warning("GEMINI_API_KEY or SUPADATA_API_KEY is missing in backend/.env")
    if not settings.auth_enabled:
        logger.info("Accounts are off (no SUPABASE_URL): running in local single-user mode")
    elif not settings.uses_postgres:
        logger.warning("Accounts are on but DATABASE_URL is empty: data stays in local SQLite and will not sync")
    yield


app = FastAPI(title="VidNotes AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request is too large."})
    return await call_next(request)


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:])
    message = first.get("msg", "Invalid request")
    return JSONResponse(status_code=422, content={"detail": f"{field}: {message}" if field else message})


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(_request: Request, exc: SQLAlchemyError):
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "A database error occurred. Please try again."})


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(settings.gemini_api_key),
        "supadata_configured": bool(settings.supadata_api_key),
        "groq_configured": bool(settings.groq_api_key),
        "auth_enabled": settings.auth_enabled,
        "cloud_database": settings.uses_postgres,
    }


@app.get("/api/config", response_model=PublicConfig)
def public_config():
    """What the browser needs to sign in. The publishable key is public by design."""
    return PublicConfig(
        auth_enabled=settings.auth_enabled,
        cloud_sync=settings.auth_enabled and settings.uses_postgres,
        supabase_url=settings.supabase_url or None,
        supabase_publishable_key=settings.supabase_publishable_key or None,
    )


app.include_router(videos_router)
app.include_router(todos_router)
app.include_router(users_router)
