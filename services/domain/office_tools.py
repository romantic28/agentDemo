"""领域服务层 - 行政事务处理场景"""

from datetime import datetime, timedelta
from uuid import uuid4

from shared.utils import get_logger
from services.tooling.registry.tool_registry import BaseTool

logger = get_logger(__name__)


class CalendarQueryTool(BaseTool):
    """日程查询工具 - 对接企业日程管理系统"""

    name = "calendar_query"
    description = "查询用户的日程安排，支持按日期、时间段、参会人筛选"
    parameters_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "用户ID"},
            "date": {"type": "string", "description": "查询日期 YYYY-MM-DD"},
            "time_range": {"type": "string", "description": "时间段 HH:MM-HH:MM"},
        },
        "required": ["user_id"],
    }

    async def execute(self, parameters: dict) -> dict:
        user_id = parameters.get("user_id", "")
        date = parameters.get("date", datetime.now().strftime("%Y-%m-%d"))
        # 模拟日程数据
        return {
            "user_id": user_id,
            "date": date,
            "events": [
                {"id": str(uuid4()), "title": "产品需求评审", "time": "09:30-10:30", "location": "会议室A", "attendees": ["张三", "李四"]},
                {"id": str(uuid4()), "title": "团队周会", "time": "14:00-15:00", "location": "线上", "attendees": ["全组"]},
                {"id": str(uuid4()), "title": "客户对接会", "time": "16:00-17:00", "location": "会议室B", "attendees": ["王五", "客户方"]},
            ],
            "total": 3,
        }


class MeetingRoomBookTool(BaseTool):
    """会议室预订工具"""

    name = "meeting_room_book"
    description = "预订会议室，需指定时间段、参会人数、设备需求"
    parameters_schema = {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
            "time_range": {"type": "string", "description": "时间段 HH:MM-HH:MM"},
            "capacity": {"type": "integer", "description": "所需容量"},
            "equipment": {"type": "array", "items": {"type": "string"}, "description": "设备需求"},
        },
        "required": ["date", "time_range"],
    }

    async def execute(self, parameters: dict) -> dict:
        date = parameters.get("date", "")
        time_range = parameters.get("time_range", "")
        capacity = parameters.get("capacity", 6)
        return {
            "status": "booked",
            "room": "会议室C-301",
            "date": date,
            "time_range": time_range,
            "capacity": capacity,
            "confirmation_id": str(uuid4())[:8],
        }


class ApprovalSubmitTool(BaseTool):
    """审批提交工具 - 对接企业OA审批系统"""

    name = "approval_submit"
    description = "提交审批申请（报销、请假、采购等）"
    parameters_schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["expense", "leave", "purchase"], "description": "审批类型"},
            "title": {"type": "string", "description": "审批标题"},
            "content": {"type": "object", "description": "审批内容详情"},
            "approver_id": {"type": "string", "description": "审批人ID"},
        },
        "required": ["type", "title"],
    }

    async def execute(self, parameters: dict) -> dict:
        return {
            "status": "submitted",
            "approval_id": str(uuid4())[:8],
            "type": parameters.get("type"),
            "title": parameters.get("title"),
            "estimated_completion": "2个工作日内",
        }


class NotificationSendTool(BaseTool):
    """消息通知工具 - 对接企业IM"""

    name = "notification_send"
    description = "发送消息通知给指定用户或群组"
    parameters_schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "接收人ID或群组ID"},
            "content": {"type": "string", "description": "消息内容"},
            "type": {"type": "string", "enum": ["text", "card", "reminder"], "description": "消息类型"},
        },
        "required": ["target", "content"],
    }

    async def execute(self, parameters: dict) -> dict:
        return {
            "status": "sent",
            "target": parameters.get("target"),
            "message_id": str(uuid4())[:8],
            "sent_at": datetime.now().isoformat(),
        }


def get_domain_tools() -> list[BaseTool]:
    """获取行政办公领域工具集"""
    return [
        CalendarQueryTool(),
        MeetingRoomBookTool(),
        ApprovalSubmitTool(),
        NotificationSendTool(),
    ]
