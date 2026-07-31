"""性能压测脚本 - 基于 Locust"""

from locust import HttpUser, task, between


class AgentUser(HttpUser):
    """模拟用户行为的压测脚本"""

    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(5)
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def chat_text(self):
        self.client.post(
            "/api/v1/chat/completions",
            json={
                "content": "帮我查询今天的会议安排",
                "tenant_id": "load_test",
                "user_id": "perf_user",
            },
        )

    @task(1)
    def chat_complex(self):
        self.client.post(
            "/api/v1/chat/completions",
            json={
                "content": "帮我预订明天下午2点到3点的会议室，6人参加，需要投影仪",
                "tenant_id": "load_test",
                "user_id": "perf_user",
            },
        )

    @task(2)
    def readiness(self):
        self.client.get("/api/v1/ready")
