from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth.router import router as auth_router
from app.api.middleware.audit import AuditMiddleware
from app.api.variants.router import router as variants_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("variant_triage_startup")
    yield
    logger.info("variant_triage_shutdown")


app = FastAPI(
    title="variant-triage",
    description="Clinical variant interpretation service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(variants_router, prefix="/variants", tags=["variants"])


@app.get("/health", description="Health check endpoint.")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
