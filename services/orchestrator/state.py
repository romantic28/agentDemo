"""LangGraph 核心状态机 - ReAct 循环实现"""

from __future__ import annotations

import json
from typing import Annotated, TypedDict, Literal
from uuid import UUID, uuid4

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from shared.schemas.task import TaskPlan, SubTask, TaskStatus, RiskLevel
from shared.utils import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    """智能体状态"""

    messages: Annotated[list, add_messages]
    conversation_id: str
    tenant_id: str
    user_id: str
    user_goal: str
    task_plan: dict | None
    current_step: int
    tool_results: list[dict]
    final_response: str
    requires_confirmation: bool
    iteration_count: int
    max_iterations: int
    error: str | None


def create_initial_state(
    conversation_id: str,
    tenant_id: str,
    user_id: str,
    user_goal: str,
    messages: list | None = None,
) -> AgentState:
    return AgentState(
        messages=messages or [],
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=user_id,
        user_goal=user_goal,
        task_plan=None,
        current_step=0,
        tool_results=[],
        final_response="",
        requires_confirmation=False,
        iteration_count=0,
        max_iterations=10,
        error=None,
    )
