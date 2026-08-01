"""内置示例工具集合"""

import httpx

from services.tooling.registry.tool_registry import BaseTool


class CalculatorTool(BaseTool):
    """计算器工具"""

    name = "calculator"
    description = "执行数学计算，支持加减乘除和常用数学函数"
    parameters_schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "数学表达式，如 '2 + 3 * 4'"},
        },
        "required": ["expression"],
    }

    async def execute(self, parameters: dict) -> dict:
        expression = parameters.get("expression", "")
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "不支持的表达式字符"}
        try:
            result = eval(expression)  # noqa: S307 - 已做字符白名单校验
            return {"expression": expression, "result": result}
        except Exception as e:
            return {"error": f"计算错误: {str(e)}"}


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name = "web_search"
    description = "搜索互联网获取实时信息"
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "最大结果数", "default": 5},
        },
        "required": ["query"],
    }

    async def execute(self, parameters: dict) -> dict:
        query = parameters.get("query", "")
        return {
            "query": query,
            "results": [
                {"title": f"搜索结果: {query}", "snippet": f"关于 {query} 的相关信息...", "url": "https://example.com"},
            ],
            "total": 1,
        }


class DataQueryTool(BaseTool):
    """数据查询工具"""

    name = "data_query"
    description = "查询企业内部数据库中的结构化数据"
    parameters_schema = {
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "数据表名"},
            "conditions": {"type": "object", "description": "查询条件"},
            "fields": {"type": "array", "items": {"type": "string"}, "description": "返回字段列表"},
        },
        "required": ["table"],
    }

    async def execute(self, parameters: dict) -> dict:
        table = parameters.get("table", "")
        conditions = parameters.get("conditions", {})
        return {
            "table": table,
            "conditions": conditions,
            "data": [{"id": 1, "status": "active", "message": f"模拟数据来自表 {table}"}],
            "total": 1,
        }


class DateTimeTool(BaseTool):
    """日期时间工具"""

    name = "datetime"
    description = "获取当前日期时间信息或进行日期计算"
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["now", "format", "diff"],
                "description": "操作类型",
            },
            "format": {"type": "string", "description": "日期格式", "default": "%Y-%m-%d %H:%M:%S"},
        },
        "required": ["action"],
    }

    async def execute(self, parameters: dict) -> dict:
        from datetime import datetime

        action = parameters.get("action", "now")
        fmt = parameters.get("format", "%Y-%m-%d %H:%M:%S")

        if action == "now":
            now = datetime.now()
            return {"datetime": now.strftime(fmt), "timestamp": now.timestamp()}
        return {"error": f"不支持的操作: {action}"}


def get_default_tools() -> list[BaseTool]:
    """获取默认工具集"""
    return [
        CalculatorTool(),
        WebSearchTool(),
        DataQueryTool(),
        DateTimeTool(),
    ]


def register_builtin_tools(registry) -> None:
    """将内置工具和领域工具注册到 ToolRegistry"""
    for tool in get_default_tools():
        registry.register(tool)

    from services.domain.office_tools import get_domain_tools

    for tool in get_domain_tools():
        registry.register(tool)
