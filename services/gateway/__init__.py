"""API网关服务 - 系统统一流量入口"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shared.config import get_settings
from shared.utils import setup_logging, get_logger
from services.gateway.routes import router as api_router
from services.gateway.middleware import TenantMiddleware, RateLimitMiddleware, TraceMiddleware, register_error_handlers
from services.gateway.tracing import setup_tracing
from services.auth.routes import router as auth_router

logger = get_logger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.app_log_level)
    logger.info("Agent Gateway starting", env=settings.app_env)
    yield
    logger.info("Agent Gateway shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Enterprise Agent System",
        description="多模态企业级智能体系统 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (order matters: last added = first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

    # Structured error handlers
    register_error_handlers(app)

    # Tracing
    setup_tracing(app)

    # Routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "gateway", "env": settings.app_env}

    # Static file serving for the React frontend SPA
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            """SPA fallback: serve index.html for all non-API routes"""
            file_path = FRONTEND_DIST / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
