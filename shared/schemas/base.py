"""基础数据模型"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """项目基础模型，统一序列化配置"""

    model_config = {"from_attributes": True, "use_enum_values": True}


class TimestampMixin(BaseModel):
    """时间戳混入"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
