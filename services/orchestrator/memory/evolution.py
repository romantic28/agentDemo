"""记忆进化引擎 - 自动学习与知识沉淀"""

from datetime import datetime
from uuid import uuid4

from shared.schemas.memory import MemoryEntry, MemoryType
from shared.utils import get_logger

logger = get_logger(__name__)


class MemoryEvolution:
    """记忆进化引擎
    
    在每次任务执行完成后，自动总结执行经验，
    沉淀为长期记忆，实现模型外的持续能力迭代。
    """

    def __init__(self):
        self._evolution_log: list[dict] = []

    async def summarize_task_experience(
        self,
        tenant_id: str,
        user_id: str,
        task_goal: str,
        execution_steps: list[dict],
        final_result: str,
        success: bool,
    ) -> MemoryEntry | None:
        """从任务执行中提取经验，生成长期记忆"""

        if not execution_steps:
            return None

        # 构建经验摘要
        tools_used = [s.get("tool", "") for s in execution_steps if s.get("tool")]
        steps_summary = f"目标: {task_goal[:100]}\n"
        steps_summary += f"工具: {', '.join(tools_used)}\n"
        steps_summary += f"结果: {'成功' if success else '失败'}\n"
        steps_summary += f"摘要: {final_result[:200]}"

        importance = 0.7 if success else 0.5

        entry = MemoryEntry(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=MemoryType.LONG_TERM,
            content=steps_summary,
            importance_score=importance,
            metadata={
                "type": "task_experience",
                "task_goal": task_goal[:200],
                "tools_used": tools_used,
                "success": success,
                "step_count": len(execution_steps),
                "evolved_at": datetime.utcnow().isoformat(),
            },
        )

        self._evolution_log.append({
            "id": str(entry.id),
            "tenant_id": tenant_id,
            "type": "experience_extraction",
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(
            "Task experience extracted",
            tenant_id=tenant_id,
            tools_used=tools_used,
            success=success,
        )

        return entry

    async def extract_user_preference(
        self,
        tenant_id: str,
        user_id: str,
        interactions: list[dict],
    ) -> list[MemoryEntry]:
        """从用户交互历史中提取偏好模式"""

        if len(interactions) < 5:
            return []

        preferences = []

        # 分析常用工具
        tool_counts: dict[str, int] = {}
        for interaction in interactions:
            for tool in interaction.get("tools_used", []):
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        frequent_tools = [t for t, c in tool_counts.items() if c >= 3]
        if frequent_tools:
            pref = MemoryEntry(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type=MemoryType.LONG_TERM,
                content=f"用户常用工具: {', '.join(frequent_tools)}",
                importance_score=0.8,
                metadata={"type": "preference", "category": "tool_usage", "tools": frequent_tools},
            )
            preferences.append(pref)

        # 分析交互时间模式
        hours = [
            datetime.fromisoformat(i["timestamp"]).hour
            for i in interactions
            if "timestamp" in i
        ]
        if hours:
            peak_hour = max(set(hours), key=hours.count)
            pref = MemoryEntry(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type=MemoryType.LONG_TERM,
                content=f"用户活跃高峰时段: {peak_hour}:00 左右",
                importance_score=0.6,
                metadata={"type": "preference", "category": "activity_pattern", "peak_hour": peak_hour},
            )
            preferences.append(pref)

        logger.info(
            "User preferences extracted",
            user_id=user_id,
            preference_count=len(preferences),
        )

        return preferences

    def get_evolution_stats(self, tenant_id: str) -> dict:
        """获取记忆进化统计"""
        tenant_logs = [l for l in self._evolution_log if l["tenant_id"] == tenant_id]
        return {
            "total_evolutions": len(tenant_logs),
            "experience_extractions": sum(1 for l in tenant_logs if l["type"] == "experience_extraction"),
        }
