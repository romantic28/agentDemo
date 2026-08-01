"""网关路由定义"""

from fastapi import APIRouter

from services.gateway.routes_chat import router as chat_router
from services.gateway.routes_health import router as health_router
from services.gateway.routes_conversations import router as conversations_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
