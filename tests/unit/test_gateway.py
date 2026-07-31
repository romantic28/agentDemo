"""Gateway API 单元测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"


@pytest.mark.anyio
async def test_readiness(client: AsyncClient):
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.anyio
async def test_chat_completions(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat/completions",
        json={
            "content": "你好，请帮我查询今天的日程",
            "tenant_id": "test_tenant",
            "user_id": "test_user",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["message"]["role"] == "assistant"


@pytest.mark.anyio
async def test_chat_with_conversation_id(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat/completions",
        json={
            "content": "继续上次的对话",
            "conversation_id": "12345678-1234-1234-1234-123456789abc",
            "tenant_id": "test_tenant",
            "user_id": "test_user",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "12345678-1234-1234-1234-123456789abc"
