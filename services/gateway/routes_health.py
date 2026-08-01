"""健康检查路由 - 验证各依赖服务连通性"""

from fastapi import APIRouter

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/ready")
async def readiness():
    """就绪探针 - 检查关键依赖"""
    settings = get_settings()
    checks = {}

    # Check PostgreSQL
    try:
        from shared.utils.database import get_engine
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {str(e)[:100]}"

    # Check Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)[:100]}"

    # Check Milvus
    try:
        from pymilvus import MilvusClient

        client = MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")
        client.list_collections()
        checks["milvus"] = "healthy"
    except Exception as e:
        checks["milvus"] = f"unhealthy: {str(e)[:100]}"

    # Check Neo4j
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        driver.verify_connectivity()
        driver.close()
        checks["neo4j"] = "healthy"
    except Exception as e:
        checks["neo4j"] = f"unhealthy: {str(e)[:100]}"

    all_healthy = all(v == "healthy" for v in checks.values())
    status_code = "ready" if all_healthy else "degraded"

    return {"status": status_code, "checks": checks}


@router.get("/metrics")
async def prometheus_metrics():
    """暴露 Prometheus 指标"""
    from fastapi.responses import PlainTextResponse
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
