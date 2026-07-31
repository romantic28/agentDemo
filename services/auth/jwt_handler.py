"""认证授权服务 - OAuth2.0 / JWT 实现"""

from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class TokenPayload:
    def __init__(self, sub: str, tenant_id: str, user_id: str, roles: list[str], exp: datetime):
        self.sub = sub
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.roles = roles
        self.exp = exp


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: str,
    tenant_id: str,
    user_id: str,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "roles": roles or [],
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI 依赖注入 - 获取当前认证用户"""
    payload = decode_token(token)
    if payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return {
        "username": payload["sub"],
        "tenant_id": payload.get("tenant_id", ""),
        "user_id": payload.get("user_id", ""),
        "roles": payload.get("roles", []),
    }


async def require_role(required_roles: list[str]):
    """角色权限校验依赖"""
    async def _check(current_user: dict = Depends(get_current_user)):
        user_roles = set(current_user.get("roles", []))
        if not user_roles.intersection(set(required_roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return _check
