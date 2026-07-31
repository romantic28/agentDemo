"""LangGraph 工作流构建 - 核心 Agent 图"""

from typing import Literal

from langgraph.graph import StateGraph, END

from shared.utils import get_logger
from services.orchestrator.state import AgentState
from services.orchestrator.llm_router import LLMRouter, ModelCapability
from services.orchestrator.planner.engine import TaskPlanner

logger = get_logger(__name__)


class AgentGraph:
    """核心 Agent 工作流图"""

    def __init__(self, llm_router: LLMRouter, tool_registry=None):
        self._llm = llm_router
        self._planner = TaskPlanner(llm_router)
        self._tool_registry = tool_registry
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("plan", self._plan_node)
        workflow.add_node("check_confirmation", self._check_confirmation_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("respond", self._respond_node)

        workflow.set_entry_point("plan")

        workflow.add_conditional_edges(
            "plan",
            self._should_confirm,
            {"confirm": "check_confirmation", "execute": "execute", "respond": "respond"},
        )

        workflow.add_conditional_edges(
            "check_confirmation",
            self._confirmation_result,
            {"approved": "execute", "rejected": "respond"},
        )

        workflow.add_conditional_edges(
            "execute",
            self._should_continue,
            {"continue": "execute", "respond": "respond"},
        )

        workflow.add_edge("respond", END)

        return workflow.compile()

    async def _plan_node(self, state: AgentState) -> AgentState:
        """规划节点 - 生成任务执行计划"""
        available_tools = []
        if self._tool_registry:
            available_tools = self._tool_registry.list_tools_schema()

        state = await self._planner.plan(state, available_tools)
        return state

    def _should_confirm(self, state: AgentState) -> Literal["confirm", "execute", "respond"]:
        """判断是否需要人工确认"""
        if state.get("requires_confirmation"):
            return "confirm"

        plan = state.get("task_plan") or {}
        subtasks = plan.get("subtasks", [])
        if not subtasks:
            return "respond"

        return "execute"

    async def _check_confirmation_node(self, state: AgentState) -> AgentState:
        """等待人工确认节点（当前版本自动通过，后续接入审批流）"""
        logger.info("Task requires confirmation", conversation_id=state["conversation_id"])
        # PoC阶段：自动通过，生产环境会接入审批流
        state["requires_confirmation"] = False
        return state

    def _confirmation_result(self, state: AgentState) -> Literal["approved", "rejected"]:
        """确认结果判断"""
        return "approved"

    async def _execute_node(self, state: AgentState) -> AgentState:
        """执行节点 - 执行 ReAct 步骤"""
        state, action_data = await self._planner.react_step(state)

        action = action_data.get("action", "respond")

        if action == "respond":
            return state

        # 执行工具调用
        if self._tool_registry and action != "respond":
            tool_params = action_data.get("action_input", {})
            if isinstance(tool_params, str):
                tool_params = {"input": tool_params}

            result = await self._tool_registry.execute(
                tool_name=action,
                parameters=tool_params,
                tenant_id=state["tenant_id"],
                user_id=state["user_id"],
            )
            state["tool_results"].append({
                "tool": action,
                "params": tool_params,
                "result": result,
                "step": state["current_step"],
            })
        else:
            state["tool_results"].append({
                "tool": action,
                "params": action_data.get("action_input", {}),
                "result": {"status": "tool_not_available"},
                "step": state["current_step"],
            })

        return state

    def _should_continue(self, state: AgentState) -> Literal["continue", "respond"]:
        """判断是否继续执行"""
        if state.get("final_response"):
            return "respond"

        if state["iteration_count"] >= state["max_iterations"]:
            state["final_response"] = "任务执行超过最大迭代次数，已终止。"
            return "respond"

        plan = state.get("task_plan") or {}
        subtasks = plan.get("subtasks", [])
        if state["current_step"] >= len(subtasks):
            return "respond"

        return "continue"

    async def _respond_node(self, state: AgentState) -> AgentState:
        """响应节点 - 生成最终用户回复"""
        if state.get("final_response"):
            return state

        # 基于工具结果生成回复
        messages = [
            {
                "role": "system",
                "content": "基于任务执行结果，生成清晰、专业的中文回复给用户。简洁明了，突出关键信息。",
            },
            {
                "role": "user",
                "content": f"用户目标: {state['user_goal']}\n\n"
                f"执行结果: {state['tool_results']}\n\n"
                "请生成最终回复:",
            },
        ]

        response = await self._llm.complete(
            messages=messages,
            capability=ModelCapability.GENERAL,
            temperature=0.5,
        )

        state["final_response"] = response["content"]
        return state

    async def run(self, state: AgentState) -> AgentState:
        """运行完整的 Agent 工作流"""
        logger.info(
            "Agent workflow started",
            conversation_id=state["conversation_id"],
            user_goal=state["user_goal"][:100],
        )

        result = await self._graph.ainvoke(state)

        logger.info(
            "Agent workflow completed",
            conversation_id=state["conversation_id"],
            iterations=result.get("iteration_count", 0),
        )

        return result
