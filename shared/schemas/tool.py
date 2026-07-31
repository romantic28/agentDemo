"""工具调用数据模型"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseModel


class ToolStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class ToolDefinition(BaseModel):
    """工具定义"""

    name: str
    description: str
    version: str = "1.0.0"
    status: ToolStatus = ToolStatus.ACTIVE
    parameters_schema: dict = Field(default_factory=dict)
    return_schema: dict = Field(default_factory=dict)
    required_permissions: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    retry_count: int = 3
    metadata: dict = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    """工具调用请求"""

    id: UUID = Field(default_factory=uuid4)
    tool_name: str
    parameters: dict = Field(default_factory=dict)
    tenant_id: str
    user_id: str
    conversation_id: UUID
    task_id: UUID | None = None
    timeout_seconds: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCallResult(BaseModel):
    """工具调用结果"""

    id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    tool_name: str
    success: bool
    result: dict | None = None
    error: str | None = None
    duration_ms: float = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
