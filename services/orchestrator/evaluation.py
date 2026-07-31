"""模型效果评测与反馈闭环 - 持续优化准确率"""

from datetime import datetime
from uuid import uuid4
from enum import Enum

from shared.schemas.base import BaseModel
from shared.utils import get_logger

logger = get_logger(__name__)


class FeedbackRating(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EvaluationRecord(BaseModel):
    """评测记录"""

    id: str = ""
    conversation_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
    user_input: str = ""
    agent_output: str = ""
    rating: FeedbackRating = FeedbackRating.NEUTRAL
    feedback_text: str = ""
    metrics: dict = {}
    created_at: datetime = datetime.utcnow()


class AccuracyOptimizer:
    """准确率持续优化引擎

    通过收集用户反馈和系统指标，构建评测数据集，
    驱动prompt优化和模型路由策略调整。
    """

    def __init__(self):
        self._feedback_store: list[EvaluationRecord] = []
        self._accuracy_metrics: dict[str, list[float]] = {}

    def record_feedback(
        self,
        conversation_id: str,
        tenant_id: str,
        user_id: str,
        user_input: str,
        agent_output: str,
        rating: FeedbackRating,
        feedback_text: str = "",
    ) -> str:
        """记录用户反馈"""
        record = EvaluationRecord(
            id=str(uuid4()),
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_input=user_input,
            agent_output=agent_output,
            rating=rating,
            feedback_text=feedback_text,
        )
        self._feedback_store.append(record)

        # 更新准确率指标
        score = 1.0 if rating == FeedbackRating.POSITIVE else (0.5 if rating == FeedbackRating.NEUTRAL else 0.0)
        self._accuracy_metrics.setdefault(tenant_id, []).append(score)

        logger.info(
            "Feedback recorded",
            conversation_id=conversation_id,
            rating=rating.value,
            tenant_id=tenant_id,
        )
        return record.id

    def get_accuracy_report(self, tenant_id: str, last_n: int = 100) -> dict:
        """获取准确率报告"""
        scores = self._accuracy_metrics.get(tenant_id, [])[-last_n:]
        if not scores:
            return {"accuracy": 0, "total_feedback": 0, "sample_size": 0}

        positive_count = sum(1 for s in scores if s == 1.0)
        negative_count = sum(1 for s in scores if s == 0.0)

        return {
            "accuracy": sum(scores) / len(scores),
            "positive_rate": positive_count / len(scores),
            "negative_rate": negative_count / len(scores),
            "total_feedback": len(self._feedback_store),
            "sample_size": len(scores),
        }

    def get_improvement_suggestions(self, tenant_id: str) -> list[str]:
        """基于反馈数据生成优化建议"""
        suggestions = []
        negative_feedbacks = [
            f for f in self._feedback_store
            if f.tenant_id == tenant_id and f.rating == FeedbackRating.NEGATIVE
        ]

        if len(negative_feedbacks) > 5:
            suggestions.append("建议审查负面反馈案例，优化对应场景的prompt模板")

        report = self.get_accuracy_report(tenant_id)
        if report["accuracy"] < 0.85:
            suggestions.append("整体准确率低于85%，建议进行场景专项优化")
        if report["negative_rate"] > 0.15:
            suggestions.append("负面反馈率超过15%，建议引入人工Review机制")

        return suggestions

    def export_evaluation_dataset(self, tenant_id: str) -> list[dict]:
        """导出评测数据集，用于模型fine-tune或prompt优化"""
        records = [f for f in self._feedback_store if f.tenant_id == tenant_id]
        return [
            {
                "input": r.user_input,
                "output": r.agent_output,
                "rating": r.rating.value,
                "feedback": r.feedback_text,
            }
            for r in records
        ]
