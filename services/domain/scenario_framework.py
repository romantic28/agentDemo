"""场景扩展框架 - 支持快速接入新的行业场景"""

from abc import ABC, abstractmethod
from typing import Any

from shared.utils import get_logger
from services.tooling.registry.tool_registry import BaseTool, ToolRegistry

logger = get_logger(__name__)


class DomainScenario(ABC):
    """领域场景基类 - 所有行业场景的标准扩展接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """场景名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """场景描述"""
        ...

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """获取场景专属工具集"""
        ...

    @abstractmethod
    def get_business_rules(self) -> dict:
        """获取场景业务规则配置"""
        ...

    def get_system_prompt_extension(self) -> str:
        """获取场景专属的系统提示词扩展"""
        return ""

    def get_knowledge_sources(self) -> list[dict]:
        """获取场景专属知识源配置"""
        return []


class ScenarioRegistry:
    """场景注册中心 - 管理所有已接入的行业场景"""

    def __init__(self, tool_registry: ToolRegistry):
        self._scenarios: dict[str, DomainScenario] = {}
        self._tool_registry = tool_registry

    def register(self, scenario: DomainScenario) -> None:
        """注册新场景"""
        self._scenarios[scenario.name] = scenario
        for tool in scenario.get_tools():
            self._tool_registry.register(tool)
        logger.info("Domain scenario registered", scenario=scenario.name)

    def get(self, name: str) -> DomainScenario | None:
        return self._scenarios.get(name)

    def list_scenarios(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description}
            for s in self._scenarios.values()
        ]

    def get_scenario_context(self, scenario_name: str) -> dict:
        """获取场景完整上下文（工具+规则+prompt）"""
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return {}
        return {
            "name": scenario.name,
            "tools": [t.name for t in scenario.get_tools()],
            "rules": scenario.get_business_rules(),
            "prompt_extension": scenario.get_system_prompt_extension(),
            "knowledge_sources": scenario.get_knowledge_sources(),
        }


# ===== 示例：财务场景扩展 =====

class FinanceScenario(DomainScenario):
    """财务场景 - 票据校验、报销审批、税务申报"""

    @property
    def name(self) -> str:
        return "finance"

    @property
    def description(self) -> str:
        return "财务办公场景：票据校验、报销审批、明细账核对、税务数据提报"

    def get_tools(self) -> list[BaseTool]:
        return [InvoiceVerifyTool(), ExpenseReportTool()]

    def get_business_rules(self) -> dict:
        return {
            "max_single_expense": 50000,
            "auto_approve_limit": 500,
            "required_attachments": ["invoice", "receipt"],
            "approval_chain": ["direct_manager", "finance_dept"],
        }

    def get_system_prompt_extension(self) -> str:
        return "你现在处理的是财务相关任务。请严格按照公司财务制度执行，所有金额操作需要二次确认。"


class InvoiceVerifyTool(BaseTool):
    name = "invoice_verify"
    description = "验证发票真伪，检查发票号、金额、日期是否合规"
    parameters_schema = {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "amount": {"type": "number"},
            "date": {"type": "string"},
        },
        "required": ["invoice_number"],
    }

    async def execute(self, parameters: dict) -> dict:
        return {
            "valid": True,
            "invoice_number": parameters.get("invoice_number"),
            "verification_status": "verified",
            "tax_amount": parameters.get("amount", 0) * 0.06,
        }


class ExpenseReportTool(BaseTool):
    name = "expense_report"
    description = "生成费用报销单并提交审批流程"
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "amount": {"type": "number"},
            "category": {"type": "string", "enum": ["travel", "meal", "office", "training"]},
            "attachments": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "amount", "category"],
    }

    async def execute(self, parameters: dict) -> dict:
        from uuid import uuid4
        return {
            "report_id": str(uuid4())[:8],
            "status": "submitted",
            "title": parameters.get("title"),
            "amount": parameters.get("amount"),
            "next_approver": "直属主管",
        }
