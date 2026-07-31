"""记忆生命周期管理 - 更新、淘汰与进化"""

from datetime import datetime, timedelta

from shared.schemas.memory import MemoryEntry, MemoryType
from shared.utils import get_logger

logger = get_logger(__name__)


class MemoryLifecycleManager:
    """记忆生命周期管理器
    
    负责记忆的创建后管理：
    - 重要性评分更新
    - 访问频率追踪
    - 过期淘汰策略
    - 记忆合并与进化
    """

    # 淘汰策略参数
    SHORT_TERM_TTL_DAYS = 7
    LONG_TERM_MIN_IMPORTANCE = 0.3
    LONG_TERM_MAX_IDLE_DAYS = 90
    MERGE_SIMILARITY_THRESHOLD = 0.85

    def compute_importance(self, entry: MemoryEntry) -> float:
        """计算记忆重要性评分 - 综合时间、频率、内容权重"""
        base_score = entry.importance_score

        # 时间衰减因子
        age_days = (datetime.utcnow() - entry.created_at).days
        time_decay = max(0.1, 1.0 - (age_days / 365.0) * 0.5)

        # 访问频率加权
        access_bonus = min(0.3, entry.access_count * 0.02)

        # 最近访问加权
        recency_bonus = 0.0
        if entry.last_accessed_at:
            idle_days = (datetime.utcnow() - entry.last_accessed_at).days
            recency_bonus = max(0, 0.2 - idle_days * 0.005)

        final_score = min(1.0, base_score * time_decay + access_bonus + recency_bonus)
        return round(final_score, 4)

    def should_evict(self, entry: MemoryEntry) -> bool:
        """判断记忆是否应被淘汰"""
        # 已过期的直接淘汰
        if entry.expires_at and datetime.utcnow() > entry.expires_at:
            return True

        # 短期记忆超期淘汰
        if entry.memory_type == MemoryType.SHORT_TERM:
            age = (datetime.utcnow() - entry.created_at).days
            return age > self.SHORT_TERM_TTL_DAYS

        # 长期记忆：重要性过低且长期未访问
        if entry.memory_type == MemoryType.LONG_TERM:
            importance = self.compute_importance(entry)
            if importance < self.LONG_TERM_MIN_IMPORTANCE:
                if entry.last_accessed_at:
                    idle_days = (datetime.utcnow() - entry.last_accessed_at).days
                    return idle_days > self.LONG_TERM_MAX_IDLE_DAYS
                else:
                    age = (datetime.utcnow() - entry.created_at).days
                    return age > self.LONG_TERM_MAX_IDLE_DAYS

        return False

    def should_promote(self, entry: MemoryEntry) -> bool:
        """判断短期记忆是否应提升为长期记忆"""
        if entry.memory_type != MemoryType.SHORT_TERM:
            return False

        # 高访问频率的短期记忆提升
        if entry.access_count >= 3:
            return True

        # 高重要性的短期记忆提升
        if entry.importance_score >= 0.7:
            return True

        return False

    async def run_eviction(self, entries: list[MemoryEntry]) -> tuple[list[str], list[str]]:
        """执行淘汰策略，返回(待删除ID列表, 待提升ID列表)"""
        to_evict = []
        to_promote = []

        for entry in entries:
            if self.should_evict(entry):
                to_evict.append(str(entry.id))
            elif self.should_promote(entry):
                to_promote.append(str(entry.id))

        logger.info(
            "Memory lifecycle sweep",
            total=len(entries),
            evicted=len(to_evict),
            promoted=len(to_promote),
        )

        return to_evict, to_promote

    def summarize_for_merge(self, entries: list[MemoryEntry]) -> str:
        """将多条相似记忆合并为一条摘要（用于记忆压缩）"""
        if not entries:
            return ""
        if len(entries) == 1:
            return entries[0].content

        contents = [e.content for e in entries]
        merged = f"[综合{len(entries)}条记忆] " + " | ".join(contents[:5])
        if len(contents) > 5:
            merged += f" ... 及其他{len(contents)-5}条"
        return merged
