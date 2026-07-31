"""图数据库存储 - Neo4j 知识图谱实现"""

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)


class GraphStore:
    """知识图谱存储 - Neo4j 实现"""

    def __init__(self):
        self._settings = get_settings()
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )
        return self._driver

    async def add_memory_node(
        self, memory_id: str, user_id: str, content: str, metadata: dict
    ) -> None:
        """添加记忆节点并建立与用户的关联"""
        driver = self._get_driver()

        def _tx(tx):
            tx.run(
                """
                MERGE (u:User {id: $user_id})
                MERGE (m:Memory {id: $memory_id})
                SET m.content = $content,
                    m.created_at = datetime(),
                    m.category = $category
                MERGE (u)-[:HAS_MEMORY]->(m)
                """,
                user_id=user_id,
                memory_id=memory_id,
                content=content[:500],
                category=metadata.get("category", "general"),
            )

        with driver.session() as session:
            session.execute_write(_tx)

        logger.debug("Graph node added", memory_id=memory_id, user_id=user_id)

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: str, properties: dict | None = None
    ) -> None:
        """添加节点间关系"""
        driver = self._get_driver()
        props = properties or {}

        def _tx(tx):
            tx.run(
                f"""
                MATCH (s {{id: $source_id}})
                MATCH (t {{id: $target_id}})
                MERGE (s)-[r:{relation_type}]->(t)
                SET r += $props
                """,
                source_id=source_id,
                target_id=target_id,
                props=props,
            )

        with driver.session() as session:
            session.execute_write(_tx)

    async def search_related(
        self, user_id: str, query: str, limit: int = 10
    ) -> list[dict]:
        """基于图关系搜索相关记忆"""
        driver = self._get_driver()

        def _tx(tx):
            result = tx.run(
                """
                MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
                WHERE m.content CONTAINS $keyword
                RETURN m.id AS id, m.content AS content, m.category AS category
                ORDER BY m.created_at DESC
                LIMIT $limit
                """,
                user_id=user_id,
                keyword=query[:50],
                limit=limit,
            )
            return [{"id": r["id"], "content": r["content"], "category": r["category"]} for r in result]

        with driver.session() as session:
            results = session.execute_read(_tx)

        return results

    async def get_user_knowledge_graph(self, user_id: str, depth: int = 2) -> dict:
        """获取用户相关的知识子图"""
        driver = self._get_driver()

        def _tx(tx):
            result = tx.run(
                """
                MATCH path = (u:User {id: $user_id})-[*1..$depth]-(n)
                RETURN nodes(path) AS nodes, relationships(path) AS rels
                LIMIT 100
                """,
                user_id=user_id,
                depth=depth,
            )
            nodes = []
            edges = []
            seen_nodes = set()
            for record in result:
                for node in record["nodes"]:
                    nid = dict(node).get("id", str(node.element_id))
                    if nid not in seen_nodes:
                        seen_nodes.add(nid)
                        nodes.append({"id": nid, "labels": list(node.labels), "properties": dict(node)})
                for rel in record["rels"]:
                    edges.append({"type": rel.type, "properties": dict(rel)})
            return {"nodes": nodes, "edges": edges}

        with driver.session() as session:
            graph = session.execute_read(_tx)

        return graph

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
