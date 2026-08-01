"""中间件 - 租户隔离、限流、trace_id、结构化错误"""

import time
import traceback
from uuid import uuid4

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared.utils import get_logger

logger = get_logger(__name__)


class TraceMiddleware(BaseHTTPMiddleware):
    """请求级 trace_id 贯穿全链路"""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid4())
        request.state.trace_id = trace_id

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"

        logger.info(
            "Request completed",
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 1),
        )
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """多租户中间件 - 从请求中提取租户ID并注入上下文"""

    SKIP_PATHS = {"/health", "/api/v1/ready", "/api/v1/auth/token", "/api/v1/metrics", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        tenant_id = self._extract_tenant_id(request)
        request.state.tenant_id = tenant_id

        logger.debug("Tenant context set", tenant_id=tenant_id, path=path)
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response

    def _extract_tenant_id(self, request: Request) -> str:
        """从请求头、JWT或query param中提取租户ID"""
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from services.auth.jwt_handler import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                return payload.get("tenant_id", "default")
            except Exception:
                pass

        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

        return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简易限流中间件"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self._requests:
            self._requests[client_ip] = []

        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self._window_seconds
        ]

        if len(self._requests[client_ip]) >= self._max_requests:
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        self._requests[client_ip].append(now)
        return await call_next(request)


def register_error_handlers(app):
    """注册全局结构化错误处理"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        trace_id = getattr(request.state, "trace_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "trace_id": trace_id,
                },
            },
            headers={"X-Trace-ID": trace_id},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.error(
            "Unhandled exception",
            trace_id=trace_id,
            error=str(exc),
            tb=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "trace_id": trace_id,
                },
            },
            headers={"X-Trace-ID": trace_id},
        )
