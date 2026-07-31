"""记忆系统单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from shared.schemas.memory import MemoryEntry, MemoryType
from services.orchestrator.memory.manager import MemoryManager


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.upsert = AsyncMock(return_value="vec-123")
    store.search = AsyncMock(return_value=[
        {"id": "mem-1", "content": "用户偏好语音交互", "score": 0.92, "metadata": {}},
    ])
    store.delete_expired = AsyncMock(return_value=3)
    return store


@pytest.fixture
def mock_graph_store():
    store = AsyncMock()
    store.add_memory_node = AsyncMock()
    store.search_related = AsyncMock(return_value=[
        {"id": "mem-2", "content": "用户经常查询日程", "category": "preference"},
    ])
    return store


@pytest.fixture
def memory_manager(mock_vector_store, mock_graph_store):
    return MemoryManager(vector_store=mock_vector_store, graph_store=mock_graph_store)


def test_working_memory_add_and_get(memory_manager):
    entry = MemoryEntry(
        tenant_id="t1", user_id="u1",
        memory_type=MemoryType.WORKING, content="当前对话上下文"
    )
    memory_manager.add_working_memory("conv-1", entry)
    memories = memory_manager.get_working_memory("conv-1")
    assert len(memories) == 1
    assert memories[0].content == "当前对话上下文"


def test_working_memory_limit(memory_manager):
    for i in range(25):
        entry = MemoryEntry(
            tenant_id="t1", user_id="u1",
            memory_type=MemoryType.WORKING, content=f"消息 {i}"
        )
        memory_manager.add_working_memory("conv-2", entry)
    memories = memory_manager.get_working_memory("conv-2")
    assert len(memories) == 20
    assert memories[0].content == "消息 5"


def test_working_memory_clear(memory_manager):
    entry = MemoryEntry(
        tenant_id="t1", user_id="u1",
        memory_type=MemoryType.WORKING, content="test"
    )
    memory_manager.add_working_memory("conv-3", entry)
    memory_manager.clear_working_memory("conv-3")
    assert memory_manager.get_working_memory("conv-3") == []


@pytest.mark.anyio
async def test_store_short_term(memory_manager, mock_vector_store):
    entry = MemoryEntry(
        tenant_id="t1", user_id="u1",
        memory_type=MemoryType.SHORT_TERM, content="用户刚刚查询了天气"
    )
    result = await memory_manager.store_short_term(entry)
    assert result == "vec-123"
    mock_vector_store.upsert.assert_called_once()


@pytest.mark.anyio
async def test_search_short_term(memory_manager, mock_vector_store):
    results = await memory_manager.search_short_term("t1", "u1", "语音")
    assert len(results) == 1
    assert results[0]["content"] == "用户偏好语音交互"


@pytest.mark.anyio
async def test_store_long_term(memory_manager, mock_vector_store, mock_graph_store):
    entry = MemoryEntry(
        tenant_id="t1", user_id="u1",
        memory_type=MemoryType.LONG_TERM, content="用户是财务部门",
        importance_score=0.9,
    )
    result = await memory_manager.store_long_term(entry)
    assert result == "vec-123"
    mock_vector_store.upsert.assert_called_once()
    mock_graph_store.add_memory_node.assert_called_once()


@pytest.mark.anyio
async def test_search_long_term_merges_results(memory_manager):
    results = await memory_manager.search_long_term("t1", "u1", "日程查询")
    assert len(results) == 2  # vector + graph results merged


@pytest.mark.anyio
async def test_retrieve_context(memory_manager):
    entry = MemoryEntry(
        tenant_id="t1", user_id="u1",
        memory_type=MemoryType.WORKING, content="当前上下文"
    )
    memory_manager.add_working_memory("conv-4", entry)

    ctx = await memory_manager.retrieve_context("t1", "u1", "conv-4", "日程")
    assert "working_memory" in ctx
    assert "short_term_memory" in ctx
    assert "long_term_memory" in ctx
    assert len(ctx["working_memory"]) == 1


@pytest.mark.anyio
async def test_evict_expired(memory_manager, mock_vector_store):
    count = await memory_manager.evict_expired("t1")
    assert count == 3
    mock_vector_store.delete_expired.assert_called_once_with(tenant_id="t1")
