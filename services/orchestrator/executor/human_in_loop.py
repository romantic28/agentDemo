"""人机协同决策机制 - 风险分级与审批流"""

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseModel
from shared.schemas.task import RiskLevel
from shared.utils import get_logger

logger = get_logger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest(BaseModel):
    """审批请求"""

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    tenant_id: str
    user_id: str
    risk_level: RiskLevel
    action_description: str
    impact_description: str
    tool_name: str | None = None
    parameters: dict = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_id: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HumanInTheLoop:
    """人机协同决策控制器

    风险分级：
    - LOW: 自动执行，仅记录审计日志
    - MEDIUM: 自动执行，事后通知相关人员
    - HIGH: 暂停执行，等待人工确认后继续
    """

    def __init__(self):
        self._pending_approvals: dict[str, ApprovalRequest] = {}

    def assess_risk(self, tool_name: str, parameters: dict) -> RiskLevel:
        """评估操作风险等级"""
        high_risk_tools = {"db_delete", "fund_transfer", "production_deploy", "data_purge"}
        medium_risk_tools = {"data_update", "batch_export", "task_create", "config_modify"}

        if tool_name in high_risk_tools:
            return RiskLevel.HIGH
        if tool_name in medium_risk_tools:
            return RiskLevel.MEDIUM

        # 参数级别的风险判断
        if parameters.get("destructive") or parameters.get("irreversible"):
            return RiskLevel.HIGH
        if parameters.get("batch_size", 0) > 100:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    async def check_and_gate(
        self,
        task_id: UUID,
        tenant_id: str,
        user_id: str,
        tool_name: str,
        parameters: dict,
        action_description: str = "",
    ) -> tuple[bool, ApprovalRequest | None]:
        """检查操作是否需要人工确认

        Returns:
            (can_proceed, approval_request)
            - can_proceed=True: 可以直接执行
            - can_proceed=False: 需要等待审批，返回审批请求
        """
        risk_level = self.assess_risk(tool_name, parameters)

        logger.info(
            "Risk assessment",
            tool_name=tool_name,
            risk_level=risk_level.value,
            task_id=str(task_id),
        )

        if risk_level == RiskLevel.LOW:
            return True, None

        if risk_level == RiskLevel.MEDIUM:
            # 中风险：执行并异步通知
            logger.info("Medium risk operation - executing with audit", tool_name=tool_name)
            return True, None

        # 高风险：创建审批请求，暂停执行
        approval = ApprovalRequest(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            risk_level=risk_level,
            action_description=action_description or f"执行工具 {tool_name}",
            impact_description=f"该操作为高风险操作，可能产生不可逆影响",
            tool_name=tool_name,
            parameters=parameters,
        )

        self._pending_approvals[str(approval.id)] = approval

        logger.warning(
            "High risk operation - approval required",
            approval_id=str(approval.id),
            tool_name=tool_name,
            task_id=str(task_id),
        )

        return False, approval

    async def approve(self, approval_id: str, approver_id: str) -> bool:
        """审批通过"""
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False

        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = approver_id
        approval.approved_at = datetime.utcnow()

        logger.info("Approval granted", approval_id=approval_id, approver_id=approver_id)
        return True

    async def reject(self, approval_id: str, approver_id: str) -> bool:
        """审批拒绝"""
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False

        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = approver_id

        logger.info("Approval rejected", approval_id=approval_id, approver_id=approver_id)
        return True

    def get_pending(self, tenant_id: str) -> list[ApprovalRequest]:
        """获取待审批列表"""
        return [
            a for a in self._pending_approvals.values()
            if a.tenant_id == tenant_id and a.status == ApprovalStatus.PENDING
        ]
