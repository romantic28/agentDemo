"""消息与会话数据模型"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ModalityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


class ModalityContent(BaseModel):
    """单个模态内容"""

    type: ModalityType
    content: str | None = None
    url: str | None = None
    metadata: dict | None = None


class Message(BaseModel):
    """单条消息"""

    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    modalities: list[ModalityContent] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class ConversationContext(BaseModel):
    """会话上下文"""

    conversation_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    user_id: str
    messages: list[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
