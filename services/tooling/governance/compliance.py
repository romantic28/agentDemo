"""安全合规检查清单 - 企业级安全验收标准"""

from dataclasses import dataclass
from enum import Enum


class ComplianceStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NOT_TESTED = "not_tested"


@dataclass
class ComplianceCheck:
    category: str
    item: str
    description: str
    status: ComplianceStatus = ComplianceStatus.NOT_TESTED
    notes: str = ""


def get_security_compliance_checklist() -> list[ComplianceCheck]:
    """获取企业级安全合规检查清单"""
    return [
        # 认证授权
        ComplianceCheck("认证授权", "JWT令牌安全", "使用强密钥签名，设置合理过期时间", ComplianceStatus.PASS),
        ComplianceCheck("认证授权", "密码加密存储", "使用bcrypt哈希，不存储明文密码", ComplianceStatus.PASS),
        ComplianceCheck("认证授权", "最小权限原则", "工具调用使用独立服务账号，权限范围最小化", ComplianceStatus.PASS),
        ComplianceCheck("认证授权", "短时令牌", "Access Token 30分钟过期", ComplianceStatus.PASS),

        # 数据隔离
        ComplianceCheck("数据隔离", "多租户数据隔离", "所有查询强制携带tenant_id过滤", ComplianceStatus.PASS),
        ComplianceCheck("数据隔离", "会话状态隔离", "使用conversation_id隔离不同会话上下文", ComplianceStatus.PASS),
        ComplianceCheck("数据隔离", "存储路径隔离", "对象存储使用租户前缀目录", ComplianceStatus.PASS),

        # 传输安全
        ComplianceCheck("传输安全", "HTTPS/TLS", "所有API通信加密传输", ComplianceStatus.PARTIAL, "开发环境HTTP，生产环境强制HTTPS"),
        ComplianceCheck("传输安全", "CORS策略", "配置跨域资源共享白名单", ComplianceStatus.PASS),

        # 输入校验
        ComplianceCheck("输入校验", "Payload安全检测", "检测SQL注入、命令注入等危险模式", ComplianceStatus.PASS),
        ComplianceCheck("输入校验", "文件上传校验", "校验文件类型、大小限制", ComplianceStatus.PASS),
        ComplianceCheck("输入校验", "参数大小限制", "请求体大小限制1MB", ComplianceStatus.PASS),

        # 审计追踪
        ComplianceCheck("审计追踪", "完整审计日志", "记录所有工具调用的入参、结果、耗时", ComplianceStatus.PASS),
        ComplianceCheck("审计追踪", "全链路追踪", "OpenTelemetry链路追踪，请求级别TraceID", ComplianceStatus.PASS),
        ComplianceCheck("审计追踪", "安全事件记录", "异常访问、越权操作实时记录告警", ComplianceStatus.PASS),

        # 人机协同
        ComplianceCheck("人机协同", "高风险操作确认", "数据删除/资金操作必须人工审批", ComplianceStatus.PASS),
        ComplianceCheck("人机协同", "操作风险分级", "LOW/MEDIUM/HIGH三级风险分类", ComplianceStatus.PASS),
        ComplianceCheck("人机协同", "异常行为熔断", "检测到异常模式自动暂停执行", ComplianceStatus.PASS),

        # 限流防护
        ComplianceCheck("限流防护", "API限流", "单IP 200次/分钟限流", ComplianceStatus.PASS),
        ComplianceCheck("限流防护", "IP黑名单", "支持IP黑白名单机制", ComplianceStatus.PARTIAL, "基础实现，需对接WAF"),
    ]


def generate_compliance_report(checks: list[ComplianceCheck]) -> dict:
    """生成合规报告摘要"""
    total = len(checks)
    passed = sum(1 for c in checks if c.status == ComplianceStatus.PASS)
    partial = sum(1 for c in checks if c.status == ComplianceStatus.PARTIAL)
    failed = sum(1 for c in checks if c.status == ComplianceStatus.FAIL)

    categories = {}
    for check in checks:
        cat = categories.setdefault(check.category, {"pass": 0, "fail": 0, "partial": 0, "total": 0})
        cat["total"] += 1
        if check.status == ComplianceStatus.PASS:
            cat["pass"] += 1
        elif check.status == ComplianceStatus.PARTIAL:
            cat["partial"] += 1
        elif check.status == ComplianceStatus.FAIL:
            cat["fail"] += 1

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "compliance_rate": f"{(passed + partial * 0.5) / total * 100:.1f}%",
        },
        "categories": categories,
        "action_items": [
            {"item": c.item, "category": c.category, "notes": c.notes}
            for c in checks
            if c.status in (ComplianceStatus.FAIL, ComplianceStatus.PARTIAL)
        ],
    }
