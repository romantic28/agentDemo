"""Prometheus 指标收集 - 全链路可观测性"""

from prometheus_client import Counter, Histogram, Gauge, Info

# ===== 业务监控指标 =====
TASK_TOTAL = Counter(
    "agent_task_total",
    "Total number of tasks processed",
    ["tenant_id", "status", "risk_level"],
)

TASK_DURATION = Histogram(
    "agent_task_duration_seconds",
    "Task execution duration in seconds",
    ["tenant_id", "task_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ACTIVE_CONVERSATIONS = Gauge(
    "agent_active_conversations",
    "Number of active conversations",
    ["tenant_id"],
)

# ===== 模型监控指标 =====
LLM_CALL_TOTAL = Counter(
    "agent_llm_call_total",
    "Total LLM API calls",
    ["provider", "model", "status"],
)

LLM_CALL_DURATION = Histogram(
    "agent_llm_call_duration_seconds",
    "LLM API call duration",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_TOKENS_USED = Counter(
    "agent_llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "type"],
)

# ===== 工具调用监控 =====
TOOL_CALL_TOTAL = Counter(
    "agent_tool_call_total",
    "Total tool calls",
    ["tool_name", "status"],
)

TOOL_CALL_DURATION = Histogram(
    "agent_tool_call_duration_seconds",
    "Tool call duration",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ===== 记忆系统监控 =====
MEMORY_RETRIEVAL_DURATION = Histogram(
    "agent_memory_retrieval_duration_seconds",
    "Memory retrieval duration",
    ["memory_type", "method"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0],
)

MEMORY_STORE_SIZE = Gauge(
    "agent_memory_store_entries",
    "Number of entries in memory store",
    ["tenant_id", "memory_type"],
)

# ===== 安全监控 =====
SECURITY_EVENT_TOTAL = Counter(
    "agent_security_event_total",
    "Security events detected",
    ["event_type", "severity"],
)

APPROVAL_PENDING = Gauge(
    "agent_approval_pending",
    "Pending approval requests",
    ["tenant_id"],
)

# ===== 系统信息 =====
SYSTEM_INFO = Info("agent_system", "Agent system information")
SYSTEM_INFO.info({"version": "0.1.0", "component": "gateway"})
