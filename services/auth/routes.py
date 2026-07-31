"""认证路由"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services.auth.jwt_handler import create_access_token, hash_password, verify_password
from shared.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 内存用户存储（PoC阶段，生产环境使用PostgreSQL）
_demo_users = {
    "admin": {
        "username": "admin",
        "hashed_password": hash_password("admin123"),
        "tenant_id": "default",
        "user_id": "admin-001",
        "roles": ["admin", "user"],
    },
    "demo": {
        "username": "demo",
        "hashed_password": hash_password("demo123"),
        "tenant_id": "demo_tenant",
        "user_id": "demo-001",
        "roles": ["user"],
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录，返回JWT令牌"""
    user = _demo_users.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        subject=user["username"],
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        roles=user["roles"],
    )

    logger.info("User logged in", username=request.username, tenant_id=user["tenant_id"])
    return TokenResponse(access_token=token)
