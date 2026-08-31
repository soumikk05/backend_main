"""
FastAPI app entrypoint — wires up all module routers, CORS, authentication, and database initialization.

Run with:
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOWED_ORIGINS
from app.auth import require_api_key
from app.db import init_db
from app.api import (
    ocr_routes,
    validation_routes,
    tampering_routes,
    face_routes,
    risk_score_routes,
    history_routes,
    intake_routes,
    screen_routes,
    operations_routes,
    auth_routes,
    evidence_routes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables upon application startup."""
    init_db()
    logging.info("Database tables initialized successfully.")
    yield


app = FastAPI(
    title="AI-Based Fake Identity & Document Screening System",
    summary="Explainable document, identity, and forgery screening API for SIH 26188.",
    description=(
        "Production backend for SIH Problem Statement 26188: OCR extraction, "
        "rule-based document validation, multi-signal tampering detection (ELA + EXIF + ORB + Stamp + Photo-Region + CNN), "
        "DeepFace face verification, intelligence registry checks, and digital audit trail persistence."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "screening", "description": "End-to-end document screening."},
        {"name": "ocr", "description": "OCR extraction and MRZ parsing."},
        {"name": "tampering", "description": "Forgery, metadata and forensic localization checks."},
        {"name": "operations", "description": "Audit chain, metrics, timelines and dashboard payloads."},
        {"name": "evidence", "description": "Role-protected evidence access and retention."},
        {"name": "authentication", "description": "JWT token issuance for role-based access."},
    ],
    lifespan=lifespan,
)

# Enable CORS using origins from configuration/environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS if CORS_ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline browser protections for Swagger and authenticated API responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(("/evidence", "/api/")) else response.headers.get("Cache-Control", "")
    return response

# Attach API routers with API Key authentication protection
auth_dependency = [Depends(require_api_key)]

app.include_router(ocr_routes.router, dependencies=auth_dependency)
app.include_router(validation_routes.router, dependencies=auth_dependency)
app.include_router(tampering_routes.router, dependencies=auth_dependency)
app.include_router(face_routes.router, dependencies=auth_dependency)
app.include_router(risk_score_routes.router, dependencies=auth_dependency)
app.include_router(history_routes.router, dependencies=auth_dependency)
app.include_router(intake_routes.router, dependencies=auth_dependency)
app.include_router(screen_routes.router, dependencies=auth_dependency)
app.include_router(operations_routes.router, dependencies=auth_dependency)
app.include_router(auth_routes.router)
app.include_router(evidence_routes.router, dependencies=auth_dependency)


@app.get("/health", tags=["health"])
def health():
    """Basic health check — exempt from authentication for uptime probes."""
    return {"status": "ok", "version": "0.3.0"}
