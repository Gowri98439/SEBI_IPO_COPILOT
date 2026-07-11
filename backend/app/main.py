import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.security.rate_limiter import limiter

from app.config import settings
from app.database import create_tables
from app.routers import auth, companies, workspaces, documents, compliance, copilot, reviews, dashboard
from app.routers import drhp as drhp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    await create_tables()

    # Index SEBI corpus into ChromaDB if not already done
    try:
        from app.ai.corpus_indexer import index_sebi_corpus, is_corpus_indexed
        if not await is_corpus_indexed():
            print("Indexing SEBI corpus into ChromaDB...")
            await index_sebi_corpus()
            print("SEBI corpus indexed successfully.")
        else:
            print("SEBI corpus already indexed — skipping.")
    except Exception as e:
        print(f"Warning: Could not index SEBI corpus: {e}")

    yield
    # ── Shutdown (nothing needed) ──────────────────────────────────────────


app = FastAPI(
    title="IPO Copilot AI",
    description=(
        "AI-powered SME IPO Offer Document Preparation and SEBI Compliance Platform. "
        "Built for the SEBI Securities Market TechSprint Hackathon 2026."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ────────────────────────────────────────────────────────────────
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routers (routers define their own prefix/tags) ────────────
# The routers below already define their own prefixes internally.
# We add the global /api/v1 prefix here.
API_V1 = "/api/v1"

# auth.router has prefix="/auth" → resolves to /api/v1/auth/...
app.include_router(auth.router, prefix=API_V1)

# companies.router has prefix="/companies" → /api/v1/companies/...
app.include_router(companies.router, prefix=API_V1)

# workspaces.router has prefix="/workspaces" → /api/v1/workspaces/...
app.include_router(workspaces.router, prefix=API_V1)

# documents.router has no prefix (uses /workspaces/... and /documents/...)
app.include_router(documents.router, prefix=API_V1)

# compliance.router has no prefix (uses /workspaces/{id}/compliance/...)
app.include_router(compliance.router, prefix=API_V1)

# copilot.router has no prefix (uses /workspaces/{id}/copilot/... and /copilot/...)
app.include_router(copilot.router, prefix=API_V1)

# reviews.router has no prefix (uses /workspaces/{id}/drafts, /drafts/{id}, etc.)
app.include_router(reviews.router, prefix=API_V1)

# dashboard.router has no prefix (uses /workspaces/{id}/dashboard)
app.include_router(dashboard.router, prefix=API_V1)

# drhp_router uses /workspaces/{id}/drhp/...
app.include_router(drhp_router.router, prefix=API_V1)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "IPO Copilot AI API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "version": "1.0.0"}


from sqlalchemy.exc import SQLAlchemyError
import asyncio

import logging as _logging
_logger = _logging.getLogger(__name__)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    _logger.error("SQLAlchemyError on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"code": "DATABASE_ERROR", "message": "A database error occurred. Please try again."},
        },
    )

@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request, exc):
    return JSONResponse(
        status_code=504,
        content={
            "success": False,
            "data": None,
            "error": {"code": "TIMEOUT_ERROR", "message": "The request timed out. Please try again later."},
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Only return string representation of exception in message, not full traceback
    error_message = str(exc) if str(exc) else "An unexpected error occurred"
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL_ERROR", "message": error_message},
        },
    )
