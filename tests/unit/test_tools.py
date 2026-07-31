"""工具注册中心单元测试"""

import pytest

from services.tooling.registry.tool_registry import ToolRegistry, BaseTool
from services.tooling.registry.builtin_tools import (
    CalculatorTool,
    WebSearchTool,
    DataQueryTool,
    DateTimeTool,
    get_default_tools,
)


def test_tool_registration():
    registry = ToolRegistry()
    tool = CalculatorTool()
    registry.register(tool)

    assert registry.get("calculator") is not None
    assert len(registry.list_tools()) == 1


def test_tool_unregistration():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.unregister("calculator")
    assert registry.get("calculator") is None


def test_list_tools_schema():
    registry = ToolRegistry()
    for tool in get_default_tools():
        registry.register(tool)

    schemas = registry.list_tools_schema()
    assert len(schemas) == 4
    assert all(s["type"] == "function" for s in schemas)
    names = [s["function"]["name"] for s in schemas]
    assert "calculator" in names
    assert "web_search" in names


@pytest.mark.anyio
async def test_calculator_tool():
    tool = CalculatorTool()
    result = await tool.execute({"expression": "2 + 3 * 4"})
    assert result["result"] == 14


@pytest.mark.anyio
async def test_calculator_invalid_expression():
    tool = CalculatorTool()
    result = await tool.execute({"expression": "import os"})
    assert "error" in result


@pytest.mark.anyio
async def test_web_search_tool():
    tool = WebSearchTool()
    result = await tool.execute({"query": "天气预报"})
    assert result["query"] == "天气预报"
    assert len(result["results"]) > 0


@pytest.mark.anyio
async def test_data_query_tool():
    tool = DataQueryTool()
    result = await tool.execute({"table": "users", "conditions": {"status": "active"}})
    assert result["table"] == "users"
    assert len(result["data"]) > 0


@pytest.mark.anyio
async def test_datetime_tool():
    tool = DateTimeTool()
    result = await tool.execute({"action": "now"})
    assert "datetime" in result
    assert "timestamp" in result


@pytest.mark.anyio
async def test_registry_execute():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    result = await registry.execute(
        tool_name="calculator",
        parameters={"expression": "10 / 2"},
        tenant_id="t1",
        user_id="u1",
    )
    assert result["success"] is True
    assert result["result"]["result"] == 5.0


@pytest.mark.anyio
async def test_registry_execute_not_found():
    registry = ToolRegistry()
    result = await registry.execute(
        tool_name="nonexistent",
        parameters={},
        tenant_id="t1",
        user_id="u1",
    )
    assert result["success"] is False
    assert "not found" in result["error"]
