"""GraphRAG 检索增强 - 向量检索 + 知识图谱关系推理"""

from shared.utils import get_logger
from services.orchestrator.memory.vector_store import VectorStore
from services.orchestrator.memory.graph_store import GraphStore

logger = get_logger(__name__)


class GraphRAGRetriever:
    """GraphRAG 混合检索器
    
    结合向量相似度检索与知识图谱关系推理，
    提升检索精度，避免记忆混淆和检索遗漏。
    """

    def __init__(self, vector_store: VectorStore, graph_store: GraphStore):
        self._vector_store = vector_store
        self._graph_store = graph_store

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        top_k: int = 10,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
    ) -> list[dict]:
        """混合检索：向量相似度 + 图谱关系推理"""

        # 1. 向量相似度检索
        vector_results = await self._vector_store.search(
            query=query,
            top_k=top_k * 2,
            filters={"tenant_id": tenant_id, "user_id": user_id},
        )

        # 2. 图谱关系检索
        graph_results = await self._graph_store.search_related(
            user_id=user_id,
            query=query,
            limit=top_k,
        )

        # 3. 融合打分
        scored_results = {}

        for r in vector_results:
            rid = r.get("id", "")
            score = r.get("score", 0) * vector_weight
            scored_results[rid] = {
                "id": rid,
                "content": r.get("content", ""),
                "score": score,
                "source": "vector",
                "metadata": r.get("metadata", {}),
            }

        for r in graph_results:
            rid = r.get("id", "")
            graph_score = graph_weight * 0.8  # 图谱命中给固定高分
            if rid in scored_results:
                scored_results[rid]["score"] += graph_score
                scored_results[rid]["source"] = "hybrid"
            else:
                scored_results[rid] = {
                    "id": rid,
                    "content": r.get("content", ""),
                    "score": graph_score,
                    "source": "graph",
                    "metadata": {"category": r.get("category", "")},
                }

        # 4. 按分数排序返回
        ranked = sorted(scored_results.values(), key=lambda x: x["score"], reverse=True)

        logger.debug(
            "GraphRAG retrieval complete",
            query=query[:50],
            vector_count=len(vector_results),
            graph_count=len(graph_results),
            merged_count=len(ranked),
        )

        return ranked[:top_k]

    async def retrieve_with_expansion(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        top_k: int = 10,
        expand_depth: int = 1,
    ) -> list[dict]:
        """带图谱扩展的检索 - 通过关系路径发现间接相关的记忆"""

        # 基础检索
        base_results = await self.retrieve(query, tenant_id, user_id, top_k=top_k)

        if not base_results or expand_depth < 1:
            return base_results

        # 获取用户知识子图用于扩展
        subgraph = await self._graph_store.get_user_knowledge_graph(
            user_id=user_id, depth=expand_depth
        )

        # 从子图节点中找到与查询相关的额外上下文
        expansion_nodes = []
        query_lower = query.lower()
        for node in subgraph.get("nodes", []):
            content = node.get("properties", {}).get("content", "")
            if content and any(keyword in content.lower() for keyword in query_lower.split()[:3]):
                expansion_nodes.append({
                    "id": node.get("id", ""),
                    "content": content,
                    "score": 0.3,
                    "source": "graph_expansion",
                    "metadata": {"labels": node.get("labels", [])},
                })

        # 合并去重
        seen_ids = {r["id"] for r in base_results}
        for node in expansion_nodes:
            if node["id"] not in seen_ids:
                base_results.append(node)
                seen_ids.add(node["id"])

        return base_results[:top_k]
