"""数据模型单元测试"""

from uuid import uuid4

from shared.schemas.message import Message, MessageRole, ModalityType, ModalityContent, ConversationContext
from shared.schemas.task import TaskPlan, SubTask, TaskStatus, RiskLevel
from shared.schemas.tool import ToolDefinition, ToolCallRequest, ToolCallResult
from shared.schemas.memory import MemoryEntry, MemoryType


def test_message_creation():
    msg = Message(role=MessageRole.USER, content="Hello")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"
    assert msg.id is not None


def test_message_with_modalities():
    msg = Message(
        role=MessageRole.USER,
        content="看看这张图片",
        modalities=[
            ModalityContent(type=ModalityType.IMAGE, url="https://example.com/img.png"),
        ],
    )
    assert len(msg.modalities) == 1
    assert msg.modalities[0].type == ModalityType.IMAGE


def test_conversation_context():
    ctx = ConversationContext(tenant_id="t1", user_id="u1")
    assert ctx.tenant_id == "t1"
    assert ctx.conversation_id is not None
    assert len(ctx.messages) == 0


def test_task_plan():
    plan = TaskPlan(
        conversation_id=uuid4(),
        user_goal="查询今天的会议安排",
        subtasks=[
            SubTask(name="query_calendar", description="查询日历", tool_name="calendar_query"),
            SubTask(name="format_result", description="格式化结果"),
        ],
    )
    assert plan.status == TaskStatus.PENDING
    assert len(plan.subtasks) == 2
    assert plan.subtasks[0].risk_level == RiskLevel.LOW


def test_tool_definition():
    tool = ToolDefinition(
        name="web_search",
        description="搜索互联网内容",
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    assert tool.name == "web_search"
    assert tool.status.value == "active"
    assert tool.timeout_seconds == 30


def test_tool_call_request():
    req = ToolCallRequest(
        tool_name="web_search",
        parameters={"query": "天气预报"},
        tenant_id="t1",
        user_id="u1",
        conversation_id=uuid4(),
    )
    assert req.tool_name == "web_search"
    assert req.id is not None


def test_tool_call_result():
    req_id = uuid4()
    result = ToolCallResult(
        request_id=req_id,
        tool_name="web_search",
        success=True,
        result={"answer": "晴天"},
        duration_ms=150.0,
    )
    assert result.success is True
    assert result.request_id == req_id


def test_memory_entry():
    entry = MemoryEntry(
        tenant_id="t1",
        user_id="u1",
        memory_type=MemoryType.LONG_TERM,
        content="用户偏好使用语音交互",
        importance_score=0.8,
    )
    assert entry.memory_type == MemoryType.LONG_TERM
    assert entry.importance_score == 0.8
    assert entry.access_count == 0
