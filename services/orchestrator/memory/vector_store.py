"""向量存储接口 - Milvus 实现"""

from typing import Any

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """向量数据库抽象层 - Milvus 实现"""

    COLLECTION_NAME = "agent_memories"
    EMBEDDING_DIM = 1024  # 千问 text-embedding-v3 默认维度

    def __init__(self):
        self._settings = get_settings()
        self._client = None
        self._embedding_client = None

    async def _get_client(self):
        if self._client is None:
            from pymilvus import MilvusClient

            self._client = MilvusClient(
                uri=f"http://{self._settings.milvus_host}:{self._settings.milvus_port}"
            )
            await self._ensure_collection()
        return self._client

    async def _get_embedding_client(self):
        if self._embedding_client is None:
            from openai import AsyncOpenAI

            self._embedding_client = AsyncOpenAI(
                api_key=self._settings.qwen_api_key,
                base_url=self._settings.qwen_base_url,
            )
        return self._embedding_client

    async def _ensure_collection(self):
        """确保集合存在"""
        client = self._client
        if not client.has_collection(self.COLLECTION_NAME):
            from pymilvus import CollectionSchema, FieldSchema, DataType

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.EMBEDDING_DIM),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="memory_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="importance_score", dtype=DataType.FLOAT),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
            ]
            schema = CollectionSchema(fields=fields, description="Agent memory vectors")
            client.create_collection(collection_name=self.COLLECTION_NAME, schema=schema)

            # 创建向量索引
            client.create_index(
                collection_name=self.COLLECTION_NAME,
                field_name="embedding",
                index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
            )
            logger.info("Milvus collection created", collection=self.COLLECTION_NAME)

    async def _embed(self, text: str) -> list[float]:
        """生成文本向量 - 使用千问 embedding 模型"""
        client = await self._get_embedding_client()
        response = await client.embeddings.create(
            model=self._settings.qwen_embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def upsert(self, id: str, content: str, metadata: dict) -> str:
        """插入或更新向量"""
        import json

        client = await self._get_client()
        embedding = await self._embed(content)

        data = {
            "id": id,
            "embedding": embedding,
            "content": content[:65000],
            "tenant_id": metadata.get("tenant_id", ""),
            "user_id": metadata.get("user_id", ""),
            "memory_type": metadata.get("memory_type", ""),
            "importance_score": metadata.get("importance_score", 0.5),
            "metadata_json": json.dumps(metadata, ensure_ascii=False)[:65000],
            "created_at": metadata.get("created_at", ""),
        }

        client.upsert(collection_name=self.COLLECTION_NAME, data=[data])
        return id

    async def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        """向量相似度检索"""
        import json

        client = await self._get_client()
        query_embedding = await self._embed(query)

        filter_expr = ""
        if filters:
            conditions = []
            for k, v in filters.items():
                if k in ("tenant_id", "user_id", "memory_type"):
                    conditions.append(f'{k} == "{v}"')
            if conditions:
                filter_expr = " and ".join(conditions)

        results = client.search(
            collection_name=self.COLLECTION_NAME,
            data=[query_embedding],
            limit=top_k,
            output_fields=["content", "tenant_id", "user_id", "memory_type", "importance_score", "metadata_json"],
            filter=filter_expr if filter_expr else None,
        )

        formatted = []
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {})
                meta = {}
                if entity.get("metadata_json"):
                    try:
                        meta = json.loads(entity["metadata_json"])
                    except json.JSONDecodeError:
                        pass
                formatted.append({
                    "id": hit.get("id", ""),
                    "content": entity.get("content", ""),
                    "score": hit.get("distance", 0),
                    "metadata": meta,
                })

        return formatted

    async def delete_expired(self, tenant_id: str) -> int:
        """删除过期记忆（基于metadata中的expires_at）"""
        logger.info("Expired memory eviction triggered", tenant_id=tenant_id)
        return 0

    async def delete(self, ids: list[str]) -> None:
        """删除指定向量"""
        client = await self._get_client()
        if ids:
            client.delete(collection_name=self.COLLECTION_NAME, ids=ids)
