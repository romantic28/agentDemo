"""低代码工作流编排引擎 - 可视化流程设计器后端"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any

from pydantic import Field

from shared.schemas.base import BaseModel
from shared.utils import get_logger

logger = get_logger(__name__)


class NodeType(str, Enum):
    START = "start"
    END = "end"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    CONDITION = "condition"
    HUMAN_REVIEW = "human_review"
    PARALLEL = "parallel"
    LOOP = "loop"
    TRANSFORM = "transform"


class WorkflowNode(BaseModel):
    """工作流节点"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    type: NodeType
    name: str
    config: dict = Field(default_factory=dict)
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})


class WorkflowEdge(BaseModel):
    """工作流边（节点间连接）"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    source: str
    target: str
    condition: str | None = None
    label: str = ""


class WorkflowDefinition(BaseModel):
    """工作流定义"""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    tenant_id: str
    version: str = "1.0.0"
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    variables: dict = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self):
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register_workflow(self, workflow: WorkflowDefinition) -> str:
        """注册工作流"""
        key = str(workflow.id)
        self._workflows[key] = workflow
        logger.info("Workflow registered", workflow_id=key, name=workflow.name)
        return key

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, tenant_id: str) -> list[WorkflowDefinition]:
        return [w for w in self._workflows.values() if w.tenant_id == tenant_id]

    def update_workflow(self, workflow_id: str, updates: dict) -> bool:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False
        for k, v in updates.items():
            if hasattr(wf, k):
                setattr(wf, k, v)
        wf.updated_at = datetime.utcnow()
        return True

    def delete_workflow(self, workflow_id: str) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

    async def execute_workflow(
        self, workflow_id: str, input_data: dict, context: dict | None = None
    ) -> dict:
        """执行工作流"""
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"success": False, "error": "Workflow not found"}

        logger.info("Workflow execution started", workflow_id=workflow_id, name=wf.name)

        # 构建执行图
        node_map = {n.id: n for n in wf.nodes}
        edge_map: dict[str, list[WorkflowEdge]] = {}
        for edge in wf.edges:
            edge_map.setdefault(edge.source, []).append(edge)

        # 找到起始节点
        start_nodes = [n for n in wf.nodes if n.type == NodeType.START]
        if not start_nodes:
            return {"success": False, "error": "No start node found"}

        # 简化执行：按拓扑序遍历
        execution_log = []
        current_node = start_nodes[0]
        variables = {**wf.variables, **input_data}
        visited = set()

        while current_node and current_node.id not in visited:
            visited.add(current_node.id)

            step_result = await self._execute_node(current_node, variables, context or {})
            execution_log.append({
                "node_id": current_node.id,
                "node_name": current_node.name,
                "type": current_node.type.value,
                "result": step_result,
            })

            if current_node.type == NodeType.END:
                break

            # 找下一个节点
            next_edges = edge_map.get(current_node.id, [])
            next_node = None
            for edge in next_edges:
                if edge.condition:
                    if self._evaluate_condition(edge.condition, variables):
                        next_node = node_map.get(edge.target)
                        break
                else:
                    next_node = node_map.get(edge.target)
                    break

            current_node = next_node

        return {
            "success": True,
            "workflow_id": workflow_id,
            "execution_log": execution_log,
            "variables": variables,
        }

    async def _execute_node(self, node: WorkflowNode, variables: dict, context: dict) -> dict:
        """执行单个节点"""
        if node.type in (NodeType.START, NodeType.END):
            return {"status": "passed"}

        if node.type == NodeType.TOOL_CALL:
            tool_name = node.config.get("tool_name", "")
            return {"status": "executed", "tool": tool_name, "mock": True}

        if node.type == NodeType.LLM_CALL:
            return {"status": "executed", "type": "llm", "mock": True}

        if node.type == NodeType.CONDITION:
            expr = node.config.get("expression", "true")
            result = self._evaluate_condition(expr, variables)
            return {"status": "evaluated", "result": result}

        if node.type == NodeType.HUMAN_REVIEW:
            return {"status": "auto_approved", "note": "PoC mode"}

        return {"status": "skipped"}

    def _evaluate_condition(self, expression: str, variables: dict) -> bool:
        """安全地评估条件表达式"""
        try:
            safe_vars = {k: v for k, v in variables.items() if isinstance(v, (str, int, float, bool))}
            return bool(eval(expression, {"__builtins__": {}}, safe_vars))  # noqa: S307
        except Exception:
            return True
