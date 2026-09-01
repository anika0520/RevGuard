"""Xperi RevGuard API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_campaigns,
    routes_copilot,
    routes_incidents,
    routes_metrics,
    routes_simulation,
)
from .api.common import ok
from .config import get_settings
from .simulation import engine
from .store.memory import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine.ensure_started()
    store.run_analysis()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Detect -> Diagnose -> Quantify -> Recommend -> Act -> Measure. "
        "Deterministic analytics; the LLM only synthesizes an evidence-grounded narrative."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    routes_campaigns,
    routes_incidents,
    routes_metrics,
    routes_simulation,
    routes_copilot,
):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return ok(
        {
            "status": "ok",
            "campaigns": len(store.world.campaigns),
            "incidents": len(store.incidents),
            "llm_provider": settings.llm_provider,
            "demo_mode": settings.demo_mode,
            "dry_run": settings.dry_run,
        }
    )
