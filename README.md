# 多模态企业级智能体系统

## 项目简介

企业级多模态智能体（Agent）系统，支持文本、语音、图像等多模态交互，具备自主决策、长时记忆、工具调用能力，面向企业办公、行业业务等场景提供全流程自动化服务。

## 技术栈

- **核心编排**: Python 3.11+ / LangGraph / FastAPI
- **模型服务**: OpenAI GPT-4o / DeepSeek R1
- **存储层**: PostgreSQL / Milvus / Neo4j / Redis / MinIO
- **前端**: React + TypeScript + Ant Design
- **基础设施**: Docker / Kubernetes / Prometheus / Grafana

## 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (前端开发)

### 本地开发

```bash
# 1. 启动基础设施
docker compose up -d
cd C:\Users\GMH\Desktop\agent
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
# 2. 安装 Python 依赖
pip install -e ".[dev,multimodal]"

# 3. 复制环境配置
cp .env.example .env

# 4. 执行数据库迁移
alembic upgrade head

# 5. 启动开发服务
python -m uvicorn services.gateway:app --reload --port 8000
```

### 运行测试

```bash
pytest tests/ -v --cov=services
```

## 项目结构

```
agent/
├── services/              # 微服务集合
│   ├── gateway/           # API网关服务
│   ├── multimodal/        # 多模态交互服务
│   ├── orchestrator/      # 核心编排服务
│   ├── domain/            # 领域服务层
│   ├── tooling/           # 工具集成服务
│   └── auth/              # 认证授权服务
├── shared/                # 共享库（数据模型、工具、配置）
├── frontend/              # 前端应用
├── infra/                 # 基础设施配置
├── tests/                 # 测试
└── scripts/               # 构建/部署脚本
```

## 开发规范

- 代码风格: ruff (PEP 8)
- 类型检查: mypy strict mode
- 提交规范: Conventional Commits
- 分支策略: Git Flow
目前对话界面：
<img width="1855" height="708" alt="微信图片_2026-07-31_235525_436" src="https://github.com/user-attachments/assets/097c8cca-1cf5-4e00-befc-edbacd6ead29" />
