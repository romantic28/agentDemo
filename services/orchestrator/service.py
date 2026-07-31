"""核心编排服务入口 - Agent 服务接口"""

from uuid import UUID

from shared.schemas.message import Message, MessageRole, ModalityContent, ModalityType
from shared.utils import get_logger
from services.orchestrator.llm_router import LLMRouter
from services.orchestrator.state import create_initial_state
from services.orchestrator.graph import AgentGraph

logger = get_logger(__name__)

_llm_router: LLMRouter | None = None
_agent_graph: AgentGraph | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def get_agent_graph() -> AgentGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = AgentGraph(
            llm_router=get_llm_router(),
            tool_registry=None,
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
