"""分层记忆管理器 - 三级记忆架构实现"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from shared.schemas.memory import MemoryEntry, MemoryType
from shared.utils import get_logger
from services.orchestrator.memory.vector_store import VectorStore
from services.orchestrator.memory.graph_store import GraphStore

logger = get_logger(__name__)


class MemoryManager:
    """分层记忆管理器
    
    三级记忆架构：
    - 工作记忆(Working): 当前会话上下文，存于内存/Redis
    - 短期记忆(Short-term): 近期交互历史，存于PostgreSQL + 向量库
    - 长期记忆(Long-term): 用户偏好/知识/经验，存于向量库 + 图数据库
    """

    def __init__(self, vector_store: VectorStore, graph_store: GraphStore):
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._working_memory: dict[str, list[MemoryEntry]] = {}

    # ===== 工作记忆 =====

    def get_working_memory(self, conversation_id: str) -> list[MemoryEntry]:
        return self._working_memory.get(conversation_id, [])

    def add_working_memory(self, conversation_id: str, entry: MemoryEntry) -> None:
        if conversation_id not in self._working_memory:
            self._working_memory[conversation_id] = []
        self._working_memory[conversation_id].append(entry)
        # 工作记忆保持最近20条
        if len(self._working_memory[conversation_id]) > 20:
            self._working_memory[conversation_id] = self._working_memory[conversation_id][-20:]

    def clear_working_memory(self, conversation_id: str) -> None:
        self._working_memory.pop(conversation_id, None)

    # ===== 短期记忆 =====

    async def store_short_term(self, entry: MemoryEntry) -> str:
        """存储短期记忆到向量库"""
        entry.memory_type = MemoryType.SHORT_TERM
        if entry.expires_at is None:
            entry.expires_at = datetime.utcnow() + timedelta(days=7)

        vector_id = await self._vector_store.upsert(
            id=str(entry.id),
            content=entry.content,
            metadata={
                "tenant_id": entry.tenant_id,
                "user_id": entry.user_id,
                "memory_type": entry.memory_type.value,
                "importance_score": entry.importance_score,
                "created_at": entry.created_at.isoformat(),
                **(entry.metadata or {}),
            },
        )
        logger.debug("Short-term memory stored", vector_id=vector_id)
        return vector_id

    async def search_short_term(
        self, tenant_id: str, user_id: str, query: str, top_k: int = 5
    ) -> list[dict]:
        """搜索短期记忆"""
        results = await self._vector_store.search(
            query=query,
            top_k=top_k,
            filters={"tenant_id": tenant_id, "user_id": user_id, "memory_type": "short_term"},
        )
        return results

    # ===== 长期记忆 =====

    async def store_long_term(self, entry: MemoryEntry) -> str:
        """存储长期记忆到向量库 + 图数据库"""
        entry.memory_type = MemoryType.LONG_TERM

        vector_id = await self._vector_store.upsert(
            id=str(entry.id),
            content=entry.content,
            metadata={
                "tenant_id": entry.tenant_id,
                "user_id": entry.user_id,
                "memory_type": entry.memory_type.value,
                "importance_score": entry.importance_score,
                "created_at": entry.created_at.isoformat(),
                **(entry.metadata or {}),
            },
        )

        # 同步到图数据库建立关联关系
        await self._graph_store.add_memory_node(
            memory_id=str(entry.id),
            user_id=entry.user_id,
            content=entry.content,
            metadata=entry.metadata or {},
        )

        logger.debug("Long-term memory stored", vector_id=vector_id, graph_synced=True)
        return vector_id

    async def search_long_term(
        self, tenant_id: str, user_id: str, query: str, top_k: int = 10
    ) -> list[dict]:
        """搜索长期记忆（向量 + 图谱混合检索）"""
        # 向量相似度检索
        vector_results = await self._vector_store.search(
            query=query,
            top_k=top_k,
            filters={"tenant_id": tenant_id, "user_id": user_id, "memory_type": "long_term"},
        )

        # 图谱关系检索
        graph_results = await self._graph_store.search_related(
            user_id=user_id,
            query=query,
            limit=top_k,
        )

        # 合并去重
        seen_ids = set()
        merged = []
        for r in vector_results + graph_results:
            rid = r.get("id", "")
            if rid not in seen_ids:
                seen_ids.add(rid)
                merged.append(r)

        return merged[:top_k]

    # ===== 综合检索 =====

    async def retrieve_context(
        self, tenant_id: str, user_id: str, conversation_id: str, query: str
    ) -> dict:
        """综合检索所有层级的记忆，构建完整上下文"""
        working = self.get_working_memory(conversation_id)
        short_term = await self.search_short_term(tenant_id, user_id, query, top_k=5)
        long_term = await self.search_long_term(tenant_id, user_id, query, top_k=5)

        return {
            "working_memory": [m.model_dump() for m in working],
            "short_term_memory": short_term,
            "long_term_memory": long_term,
        }

    # ===== 记忆淘汰 =====

    async def evict_expired(self, tenant_id: str) -> int:
        """淘汰过期记忆"""
        count = await self._vector_store.delete_expired(tenant_id=tenant_id)
        logger.info("Expired memories evicted", tenant_id=tenant_id, count=count)
        return count
