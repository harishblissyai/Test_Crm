"""
Application entry point.

create_app() builds and returns the FastAPI instance.
The module-level `app` variable is what uvicorn loads.

Usage:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.auth import router as auth_router
from app.api.clients import router as client_router
from app.api.health import router as health_router
from app.api.tenants import router as tenant_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.middleware import RequestIDMiddleware, TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    setup_logging()
    yield
    # Dispose the DB connection pool on shutdown
    from app.db.session import engine
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="White-label multi-tenant CRM — BlissyAI",
        version="0.1.0",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # ── Rate limiter ───────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ───────────────────────────────────────────────────
    # Must be added before custom middleware so preflight requests are handled
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware (last added = outermost = runs first) ─
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Exception handlers ─────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health_router, prefix=settings.API_PREFIX)
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(tenant_router, prefix=settings.API_PREFIX)
    app.include_router(client_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
