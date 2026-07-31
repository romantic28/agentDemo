"""多租户中间件 - 租户隔离与路由"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared.utils import get_logger

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """多租户中间件 - 从请求中提取租户ID并注入上下文"""

    SKIP_PATHS = {"/health", "/api/v1/ready", "/api/v1/auth/token", "/docs", "/openapi.json"}

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
        # 优先从header提取
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # 从Authorization JWT中提取
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from services.auth.jwt_handler import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                return payload.get("tenant_id", "default")
            except Exception:
                pass

        # 从query param提取
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
        import time

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self._requests:
            self._requests[client_ip] = []

        # 清理过期记录
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self._window_seconds
        ]

        if len(self._requests[client_ip]) >= self._max_requests:
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        self._requests[client_ip].append(now)
        return await call_next(request)
