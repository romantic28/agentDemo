"""任务规划数据模型"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SubTask(BaseModel):
    """子任务"""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    tool_name: str | None = None
    tool_params: dict = Field(default_factory=dict)
    dependencies: list[UUID] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    status: TaskStatus = TaskStatus.PENDING
    result: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskPlan(BaseModel):
    """任务执行计划"""

    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    user_goal: str
    reasoning: str = ""
    subtasks: list[SubTask] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    requires_confirmation: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
