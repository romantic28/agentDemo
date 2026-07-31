"""安全治理组件 - 工具调用安全校验与审计"""

import time
from datetime import datetime
from uuid import uuid4

from shared.utils import get_logger

logger = get_logger(__name__)


class SecurityGovernance:
    """安全治理引擎 - 工具调用的多维度安全校验"""

    # 敏感操作关键词
    DANGEROUS_PATTERNS = ["drop", "delete all", "truncate", "rm -rf", "format"]

    # 允许的目标域名白名单
    ALLOWED_DOMAINS = {"localhost", "127.0.0.1", "*.internal.company.com"}

    def __init__(self):
        self._audit_log: list[dict] = []

    def validate_payload(self, tool_name: str, parameters: dict) -> tuple[bool, str]:
        """Payload 安全检测"""
        params_str = str(parameters).lower()

        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in params_str:
                self._log_security_event("payload_blocked", tool_name, f"Dangerous pattern: {pattern}")
                return False, f"安全策略拦截：检测到危险操作模式 '{pattern}'"

        # 检查参数大小
        import json
        payload_size = len(json.dumps(parameters, default=str))
        if payload_size > 1_000_000:  # 1MB
            return False, "安全策略拦截：Payload 超过大小限制"

        return True, ""

    def validate_target(self, url: str) -> tuple[bool, str]:
        """目标地址安全校验"""
        if not url:
            return True, ""

        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # 阻止内网穿透（SSRF防护）
        private_prefixes = ["10.", "172.16.", "172.17.", "192.168.", "169.254."]
        if any(hostname.startswith(p) for p in private_prefixes):
            if hostname not in ("localhost", "127.0.0.1"):
                self._log_security_event("ssrf_blocked", "", f"Private IP access: {hostname}")
                return False, "安全策略拦截：禁止访问内网地址"

        return True, ""

    def validate_permissions(self, tenant_id: str, user_roles: list[str], tool_name: str) -> tuple[bool, str]:
        """权限校验"""
        # 高权限工具需要admin角色
        admin_only_tools = {"db_delete", "production_deploy", "config_modify", "user_manage"}
        if tool_name in admin_only_tools and "admin" not in user_roles:
            self._log_security_event("permission_denied", tool_name, f"Roles: {user_roles}")
            return False, f"权限不足：工具 '{tool_name}' 需要管理员权限"

        return True, ""

    def audit_log(
        self, tenant_id: str, user_id: str, tool_name: str,
        parameters: dict, result: dict, duration_ms: float
    ) -> None:
        """记录审计日志"""
        entry = {
            "id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "tool_name": tool_name,
            "parameters_summary": str(parameters)[:500],
            "success": result.get("success", False),
            "duration_ms": duration_ms,
            "error": result.get("error"),
        }
        self._audit_log.append(entry)

        # 保留最近10000条
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

        logger.debug("Audit logged", tool_name=tool_name, user_id=user_id)

    def get_audit_logs(self, tenant_id: str, limit: int = 100) -> list[dict]:
        """获取审计日志"""
        filtered = [log for log in self._audit_log if log["tenant_id"] == tenant_id]
        return filtered[-limit:]

    def _log_security_event(self, event_type: str, tool_name: str, detail: str) -> None:
        """记录安全事件"""
        logger.warning(
            "Security event",
            event_type=event_type,
            tool_name=tool_name,
            detail=detail,
        )
