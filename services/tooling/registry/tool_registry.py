"""工具注册中心 - 标准化工具管理与调用"""

import asyncio
import time
from typing import Any, Callable, Awaitable
from uuid import uuid4

from shared.schemas.tool import ToolDefinition, ToolCallRequest, ToolCallResult, ToolStatus
from shared.utils import get_logger

logger = get_logger(__name__)


class BaseTool:
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters_schema: dict = {}

    async def execute(self, parameters: dict) -> dict:
        raise NotImplementedError


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        self._definitions[tool.name] = ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters_schema=tool.parameters_schema,
        )
        logger.info("Tool registered", tool_name=tool.name)

    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        self._tools.pop(tool_name, None)
        self._definitions.pop(tool_name, None)

    def get(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    def list_tools_schema(self) -> list[dict]:
        """返回适配LLM function calling的工具描述"""
        return [
            {
                "type": "function",
                "function": {
                    "name": d.name,
                    "description": d.description,
                    "parameters": d.parameters_schema,
                },
            }
            for d in self._definitions.values()
            if d.status == ToolStatus.ACTIVE
        ]

    async def execute(
        self,
        tool_name: str,
        parameters: dict,
        tenant_id: str,
        user_id: str,
        timeout: int | None = None,
    ) -> dict:
        """执行工具调用"""
        tool = self._tools.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        start_time = time.time()
        request_id = str(uuid4())

        logger.info(
            "Tool execution started",
            request_id=request_id,
            tool_name=tool_name,
            tenant_id=tenant_id,
        )

        try:
            effective_timeout = timeout or 30
            result = await asyncio.wait_for(
                tool.execute(parameters),
                timeout=effective_timeout,
            )
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Tool execution completed",
                request_id=request_id,
                tool_name=tool_name,
                duration_ms=duration_ms,
                success=True,
            )

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
                "request_id": request_id,
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning("Tool execution timeout", tool_name=tool_name, timeout=timeout)
            return {
                "success": False,
                "error": f"Tool '{tool_name}' execution timed out",
                "duration_ms": duration_ms,
                "request_id": request_id,
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
                "request_id": request_id,
            }
