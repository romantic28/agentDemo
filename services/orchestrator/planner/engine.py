"""任务规划引擎 - 基于 ReAct 框架的动态任务规划"""

import json
import re
from uuid import uuid4

from shared.schemas.task import TaskPlan, SubTask, TaskStatus, RiskLevel
from shared.utils import get_logger
from services.orchestrator.llm_router import LLMRouter, ModelCapability
from services.orchestrator.state import AgentState

logger = get_logger(__name__)


def _extract_json(text: str) -> dict | None:
    """从 LLM 返回内容中提取 JSON，处理 <think> 标签和 markdown 代码块"""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    code_block = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    start = -1

    return None


PLANNING_SYSTEM_PROMPT = (
    "你是一个企业级智能体的任务规划引擎。你的职责是：\n"
    "1. 分析用户的业务目标\n"
    "2. 将复杂目标拆解为可执行的子任务\n"
    "3. 确定子任务的依赖关系和执行顺序\n"
    "4. 为每个子任务选择合适的工具\n"
    "5. 评估每个操作的风险等级\n"
    "\n"
    "你必须以JSON格式输出任务计划，格式如下：\n"
    '{{\n'
    '    "reasoning": "你的推理过程",\n'
    '    "subtasks": [\n'
    '        {{\n'
    '            "name": "子任务名称",\n'
    '            "description": "子任务描述",\n'
    '            "tool_name": "工具名称或null",\n'
    '            "tool_params": {{}},\n'
    '            "dependencies": [],\n'
    '            "risk_level": "low|medium|high"\n'
    '        }}\n'
    '    ],\n'
    '    "requires_confirmation": false\n'
    '}}\n'
    "\n"
    "风险等级判断标准：\n"
    "- low: 数据查询、消息发送、文档创建草稿等只读或低影响操作\n"
    "- medium: 数据更新、批量导出、任务创建等可逆操作\n"
    "- high: 数据删除、资金操作、生产环境修改等不可逆操作\n"
    "\n"
    "可用工具列表：\n"
    "{available_tools}"
)

REACT_SYSTEM_PROMPT = (
    "你是一个企业级智能体。基于ReAct框架，你需要：\n"
    "1. Thought: 思考当前应该做什么\n"
    "2. Action: 选择并执行工具\n"
    "3. Observation: 观察工具返回结果\n"
    "4. 重复以上过程直到任务完成\n"
    "\n"
    "当前任务计划：\n"
    "{task_plan}\n"
    "\n"
    "当前执行到第 {current_step} 步。\n"
    "\n"
    "已有的工具调用结果：\n"
    "{tool_results}\n"
    "\n"
    "请决定下一步操作。如果任务已完成，直接生成最终回复。\n"
    "输出格式为JSON：\n"
    '{{\n'
    '    "thought": "你的思考过程",\n'
    '    "action": "tool_name 或 respond",\n'
    '    "action_input": {{}} 或 "最终回复内容"\n'
    '}}'
)


class TaskPlanner:
    """任务规划器"""

    def __init__(self, llm_router: LLMRouter):
        self._llm = llm_router

    async def plan(self, state: AgentState, available_tools: list[dict]) -> AgentState:
        """生成任务执行计划"""
        tools_desc = json.dumps(available_tools, ensure_ascii=False, indent=2)
        system_prompt = PLANNING_SYSTEM_PROMPT.format(available_tools=tools_desc)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户目标: {state['user_goal']}"},
        ]

        for msg in state["messages"][-10:]:
            if hasattr(msg, "content"):
                messages.append({"role": getattr(msg, "type", "user"), "content": msg.content})

        response = await self._llm.complete(
            messages=messages,
            capability=ModelCapability.REASONING,
            temperature=0.3,
        )

        plan_data = _extract_json(response["content"])
        if plan_data is None:
            plan_data = {
                "reasoning": "直接回复用户",
                "subtasks": [],
                "requires_confirmation": False,
            }

        state["task_plan"] = plan_data
        state["requires_confirmation"] = plan_data.get("requires_confirmation", False)

        for st in plan_data.get("subtasks", []):
            if st.get("risk_level") == "high":
                state["requires_confirmation"] = True
                break

        logger.info(
            "Task plan generated",
            subtask_count=len(plan_data.get("subtasks", [])),
            requires_confirmation=state["requires_confirmation"],
        )

        return state

    async def react_step(self, state: AgentState) -> tuple[AgentState, dict]:
        """执行一步 ReAct 循环"""
        plan = state["task_plan"] or {}
        tool_results_str = json.dumps(state["tool_results"], ensure_ascii=False, indent=2)

        system_prompt = REACT_SYSTEM_PROMPT.format(
            task_plan=json.dumps(plan, ensure_ascii=False, indent=2),
            current_step=state["current_step"],
            tool_results=tool_results_str,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_goal"]},
        ]

        response = await self._llm.complete(
            messages=messages,
            capability=ModelCapability.REASONING,
            temperature=0.2,
        )

        action_data = _extract_json(response["content"])
        if action_data is None:
            action_data = {"thought": "无法解析", "action": "respond", "action_input": response["content"]}

        logger.info(
            "ReAct step",
            thought=action_data.get("thought", "")[:100],
            action=action_data.get("action"),
            step=state["current_step"],
        )

        if action_data.get("action") == "respond":
            state["final_response"] = action_data.get("action_input", "")
        else:
            state["current_step"] += 1

        state["iteration_count"] += 1
        return state, action_data
