import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware.request_logging import RequestLoggingMiddleware
from app.api.routes import (
    auth,
    certification,
    chat,
    compliance,
    documents,
    hallmarking,
    laboratories,
    notifications,
    reports,
    standards,
)
from app.config import settings
from app.database.connection import check_database
from app.database.schemas import HealthStatus
from app.rag.pinecone_store import get_store
from app.services.llm_service import get_llm
from app.utils.errors import AppError
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
    db_ok, db_msg = check_database()
    logger.info("Startup checks: database=%s llm=%s pinecone=%s", db_msg, get_llm().status(),
                "configured" if settings.pinecone_configured else "not configured")
    if not settings.JWT_SECRET_KEY:
        logger.warning("JWT_SECRET_KEY is not set; authentication endpoints will return 503.")
    yield


app = FastAPI(
    title="BIS SAATHI API",
    description="Agentic AI-powered Indian Standards and Certification Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "x-request-id"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]} for err in exc.errors()
    ]
    first = errors[0] if errors else {"field": "", "message": "Invalid input"}
    detail = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(status_code=422, content={"detail": detail, "code": "validation_error", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again.", "code": "internal_error",
                 "request_id": request_id},
    )


for router in (auth.router, chat.router, documents.router, standards.router, certification.router,
               laboratories.router, hallmarking.router, compliance.router, reports.router, notifications.router):
    app.include_router(router)


@app.get("/api/health", response_model=HealthStatus, tags=["System"])
def health() -> HealthStatus:
    db_ok, db_msg = check_database()
    llm_status = get_llm().status()
    pinecone_status = get_store().health()
    overall = "ok" if db_ok and llm_status.startswith("ready") and pinecone_status.startswith("connected") else "degraded"
    return HealthStatus(
        status=overall,
        database=db_msg,
        pinecone=pinecone_status,
        llm=llm_status,
        embedding_model=f"{settings.EMBEDDING_MODEL} ({settings.EMBEDDING_DIMENSION}-dim, Pinecone Inference)",
    )


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": "BIS SAATHI API", "docs": "/docs", "health": "/api/health"}
