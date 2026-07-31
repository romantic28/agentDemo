"""核心编排层单元测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.orchestrator.state import AgentState, create_initial_state
from services.orchestrator.llm_router import LLMRouter, ModelCapability, ModelProvider, MODEL_ROUTING_TABLE


def test_create_initial_state():
    state = create_initial_state(
        conversation_id="conv-123",
        tenant_id="t1",
        user_id="u1",
        user_goal="查询今日会议",
    )
    assert state["conversation_id"] == "conv-123"
    assert state["tenant_id"] == "t1"
    assert state["user_goal"] == "查询今日会议"
    assert state["iteration_count"] == 0
    assert state["max_iterations"] == 10
    assert state["task_plan"] is None
    assert state["final_response"] == ""


def test_model_routing_table():
    assert MODEL_ROUTING_TABLE[ModelCapability.REASONING] == ModelProvider.DEEPSEEK
    assert MODEL_ROUTING_TABLE[ModelCapability.VISION] == ModelProvider.OPENAI
    assert MODEL_ROUTING_TABLE[ModelCapability.GENERAL] == ModelProvider.OPENAI
    assert MODEL_ROUTING_TABLE[ModelCapability.CODE] == ModelProvider.DEEPSEEK


def test_llm_router_route():
    router = LLMRouter()
    assert router.route(ModelCapability.REASONING) == ModelProvider.DEEPSEEK
    assert router.route(ModelCapability.VISION) == ModelProvider.OPENAI
    assert router.route(ModelCapability.GENERAL) == ModelProvider.OPENAI


@pytest.mark.anyio
async def test_planner_plan():
    """测试规划引擎生成任务计划"""
    from services.orchestrator.planner.engine import TaskPlanner

    mock_router = AsyncMock(spec=LLMRouter)
    mock_router.complete = AsyncMock(return_value={
        "content": '{"reasoning": "直接查询日历", "subtasks": [{"name": "query_cal", "description": "查日历", "tool_name": "calendar", "tool_params": {}, "dependencies": [], "risk_level": "low"}], "requires_confirmation": false}',
        "tool_calls": [],
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "provider": "openai",
        "model": "gpt-4o",
    })

    planner = TaskPlanner(mock_router)
    state = create_initial_state(
        conversation_id="conv-1",
        tenant_id="t1",
        user_id="u1",
        user_goal="查询今日会议",
    )

    result = await planner.plan(state, available_tools=[])
    assert result["task_plan"] is not None
    assert result["task_plan"]["reasoning"] == "直接查询日历"
    assert len(result["task_plan"]["subtasks"]) == 1
    assert result["requires_confirmation"] is False


@pytest.mark.anyio
async def test_planner_high_risk_triggers_confirmation():
    """测试高风险操作触发人工确认"""
    from services.orchestrator.planner.engine import TaskPlanner

    mock_router = AsyncMock(spec=LLMRouter)
    mock_router.complete = AsyncMock(return_value={
        "content": '{"reasoning": "需要删除数据", "subtasks": [{"name": "delete_data", "description": "删除记录", "tool_name": "db_delete", "tool_params": {}, "dependencies": [], "risk_level": "high"}], "requires_confirmation": false}',
        "tool_calls": [],
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "provider": "deepseek",
        "model": "deepseek-reasoner",
    })

    planner = TaskPlanner(mock_router)
    state = create_initial_state(
        conversation_id="conv-2",
        tenant_id="t1",
        user_id="u1",
        user_goal="删除所有过期数据",
    )

    result = await planner.plan(state, available_tools=[])
    assert result["requires_confirmation"] is True


@pytest.mark.anyio
async def test_react_step_respond():
    """测试ReAct步骤 - 直接回复"""
    from services.orchestrator.planner.engine import TaskPlanner

    mock_router = AsyncMock(spec=LLMRouter)
    mock_router.complete = AsyncMock(return_value={
        "content": '{"thought": "任务已完成", "action": "respond", "action_input": "今天有3个会议"}',
        "tool_calls": [],
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "provider": "deepseek",
        "model": "deepseek-reasoner",
    })

    planner = TaskPlanner(mock_router)
    state = create_initial_state(
        conversation_id="conv-3",
        tenant_id="t1",
        user_id="u1",
        user_goal="查询会议",
    )
    state["task_plan"] = {"subtasks": []}

    result_state, action_data = await planner.react_step(state)
    assert action_data["action"] == "respond"
    assert result_state["final_response"] == "今天有3个会议"
