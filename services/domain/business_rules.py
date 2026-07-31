"""领域业务规则引擎 - 行政事务场景"""

from shared.utils import get_logger

logger = get_logger(__name__)


class OfficeBusinessRules:
    """行政办公业务规则集合"""

    # 会议室预订规则
    ROOM_BOOKING_MAX_HOURS = 4
    ROOM_BOOKING_ADVANCE_DAYS = 14
    ROOM_BOOKING_MIN_ADVANCE_MINUTES = 30

    # 审批规则
    EXPENSE_AUTO_APPROVE_LIMIT = 500  # 500元以下自动审批
    LEAVE_MAX_DAYS_NO_APPROVAL = 1   # 1天以内免审批

    # 通知规则
    NOTIFICATION_QUIET_HOURS = (22, 8)  # 22:00-08:00 免打扰

    def validate_room_booking(self, params: dict) -> tuple[bool, str]:
        """校验会议室预订请求"""
        time_range = params.get("time_range", "")
        if time_range:
            parts = time_range.split("-")
            if len(parts) == 2:
                start_h, start_m = map(int, parts[0].split(":"))
                end_h, end_m = map(int, parts[1].split(":"))
                duration_hours = (end_h * 60 + end_m - start_h * 60 - start_m) / 60
                if duration_hours > self.ROOM_BOOKING_MAX_HOURS:
                    return False, f"单次预订不能超过{self.ROOM_BOOKING_MAX_HOURS}小时"

        capacity = params.get("capacity", 0)
        if capacity > 50:
            return False, "超出最大会议室容量，请联系行政部门"

        return True, ""

    def validate_expense(self, params: dict) -> tuple[bool, str, bool]:
        """校验报销申请，返回(是否有效, 错误信息, 是否需要审批)"""
        content = params.get("content", {})
        amount = content.get("amount", 0)

        if amount <= 0:
            return False, "报销金额必须大于0", False
        if amount > 50000:
            return False, "超过单笔报销上限(50000元)，请拆分", False

        needs_approval = amount > self.EXPENSE_AUTO_APPROVE_LIMIT
        return True, "", needs_approval

    def validate_notification(self, params: dict) -> tuple[bool, str]:
        """校验通知发送请求"""
        from datetime import datetime
        now = datetime.now()
        quiet_start, quiet_end = self.NOTIFICATION_QUIET_HOURS

        if now.hour >= quiet_start or now.hour < quiet_end:
            msg_type = params.get("type", "text")
            if msg_type != "reminder":
                return True, "当前为免打扰时间，消息将延迟到08:00发送"

        return True, ""

    def get_conflict_suggestions(self, events: list[dict], requested_time: str) -> list[str]:
        """当日程冲突时生成调整建议"""
        suggestions = []
        # 寻找空闲时段
        busy_times = set()
        for event in events:
            busy_times.add(event.get("time", ""))

        available_slots = ["08:00-09:00", "10:30-11:30", "13:00-14:00", "15:00-16:00", "17:00-18:00"]
        for slot in available_slots:
            if slot not in busy_times:
                suggestions.append(f"建议调整到 {slot}")
                if len(suggestions) >= 3:
                    break

        return suggestions
