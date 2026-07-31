"""健康检查路由"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/ready")
async def readiness():
    return {"status": "ready"}
