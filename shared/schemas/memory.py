"""记忆系统数据模型"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseModel


class MemoryType(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class MemoryEntry(BaseModel):
    """记忆条目"""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    user_id: str
    memory_type: MemoryType
    content: str
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)
    source_conversation_id: UUID | None = None
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
