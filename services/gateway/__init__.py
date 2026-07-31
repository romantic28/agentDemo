"""API网关服务 - 系统统一流量入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.utils import setup_logging, get_logger
from services.gateway.routes import router as api_router
from services.gateway.middleware import TenantMiddleware, RateLimitMiddleware
from services.gateway.tracing import setup_tracing
from services.auth.routes import router as auth_router

logger = get_logger(__name__)


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
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

    # Tracing
    setup_tracing(app)

    # Routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "gateway", "env": settings.app_env}

    return app


app = create_app()
