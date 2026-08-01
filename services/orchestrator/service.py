"""核心编排服务入口 - Agent 服务接口"""

from typing import AsyncIterator
from uuid import UUID

from shared.schemas.message import Message, MessageRole, ModalityContent, ModalityType
from shared.utils import get_logger
from services.orchestrator.llm_router import LLMRouter, ModelCapability
from services.orchestrator.state import create_initial_state
from services.orchestrator.graph import AgentGraph
from services.orchestrator.memory.manager import MemoryManager
from services.orchestrator.memory.vector_store import VectorStore
from services.orchestrator.memory.graph_store import GraphStore
from services.tooling.registry.tool_registry import ToolRegistry
from services.tooling.registry.builtin_tools import register_builtin_tools

logger = get_logger(__name__)

_llm_router: LLMRouter | None = None
_agent_graph: AgentGraph | None = None
_tool_registry: ToolRegistry | None = None
_memory_manager: MemoryManager | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        register_builtin_tools(_tool_registry)
    return _tool_registry


def get_memory_manager() -> MemoryManager | None:
    global _memory_manager
    if _memory_manager is None:
        try:
            vector_store = VectorStore()
            graph_store = GraphStore()
            _memory_manager = MemoryManager(vector_store=vector_store, graph_store=graph_store)
            logger.info("MemoryManager initialized")
        except Exception as e:
            logger.warning("MemoryManager initialization failed, running without memory", error=str(e))
            _memory_manager = None
    return _memory_manager


def get_agent_graph() -> AgentGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = AgentGraph(
            llm_router=get_llm_router(),
            tool_registry=get_tool_registry(),
            memory_manager=get_memory_manager(),
        )
    return _agent_graph


async def process_message(
    conversation_id: str,
    tenant_id: str,
    user_id: str,
    content: str,
    messages_history: list | None = None,
) -> str:
    """处理用户消息，返回Agent响应"""
    graph = get_agent_graph()

    state = create_initial_state(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=user_id,
        user_goal=content,
        messages=messages_history,
    )

    result = await graph.run(state)
    return result.get("final_response", "抱歉，我暂时无法处理您的请求。")


async def stream_message(
    conversation_id: str,
    tenant_id: str,
    user_id: str,
    content: str,
    messages_history: list | None = None,
) -> AsyncIterator[str]:
    """流式处理用户消息，逐 token 返回"""
    llm = get_llm_router()

    messages = []
    if messages_history:
        messages.extend(messages_history)

    messages.append({"role": "system", "content": "你是一个企业级智能助手，请用专业、清晰的中文回复用户。"})
    messages.append({"role": "user", "content": content})

    async for token in llm.stream(messages=messages, capability=ModelCapability.GENERAL):
        yield token
