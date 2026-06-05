# NexusAI — 智能内容采集与管理系统

基于 AI Agent 的全链路内容聚合平台，支持 RSS/网页自动采集、语义去重、多语言翻译、审批工作流和可视化仪表盘。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Ant Design 5, ECharts, Zustand, Vite |
| 网关 | Spring Cloud Gateway 2023.0.1 |
| 后端 | Spring Boot 3.2.5, MyBatis-Plus 3.5.7, JWT, Redis |
| AI 中台 | FastAPI, LangGraph, feedparser, Playwright, OpenAI |
| 数据库 | MySQL 8.0 (InnoDB, utf8mb4) |
| 消息队列 | RocketMQ (可选) |
| 向量搜索 | Milvus (可选) |

## 项目结构

```
NexusAI/
├── frontend/          # React 前端 (:5173)
├── gateway/           # Spring Cloud Gateway (:8080)
├── nexus-java/        # Java 后端 (:8081)
├── nexus-python/      # Python AI 中台 (:8000)
├── infra/             # Docker Compose + SQL 初始化脚本
├── scripts/           # 数据库初始化和示例数据脚本
└── docs/              # 文档
```

## 功能模块

- **认证系统** — JWT 登录/注册，BCrypt 密码加密，路由守卫，水平越权防护
- **仪表盘** — 4 项统计指标 + ECharts 平台分布饼图 + 24 小时采集趋势折线图
- **订阅管理** — 创建/编辑/删除 RSS 订阅规则，手动触发采集，关键词配置
- **内容中心** — 分页浏览，标题搜索，可展开详情查看完整正文
- **审批工单** — 高风险操作需管理员审批，支持通过/拒绝/评论
- **通知中心** — 采集完成/审批结果/系统消息推送，支持已读标记
- **AI 采集流水线** — RSS 抓取 → 网页刮取补全 → LLM 翻译 → 哈希去重 → 存储
- **审计日志** — 全操作记录，管理员可追溯

## 快速开始

### 环境要求

- JDK 24+ (Lombok 1.18.38)
- Maven 3.9+
- Python 3.11+
- Node.js 24+
- MySQL 8.0
- Redis 7

### 1. 数据库初始化

```bash
pip install pymysql
python scripts/init_db.py
python scripts/seed_data.py   # 插入示例数据（可选）
```

### 2. 启动服务

```bash
# Java 后端 (:8081)
cd nexus-java
mvn spring-boot:run

# Python AI 中台 (:8000)
cd nexus-python
pip install -r requirements.txt
uvicorn app.main:app --reload

# Gateway 网关 (:8080)
cd gateway
mvn spring-boot:run

# 前端 (:5173)
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`

### 3. 使用 Docker Compose（可选）

```bash
cd infra
docker-compose up -d mysql redis   # 仅启动必需服务
```

## API 概览

### Java REST API (`/api/java`)

| 模块 | 端点 | 说明 |
|------|------|------|
| Auth | POST /auth/register, /auth/login | 注册/登录 |
| Subscription | CRUD /subscriptions, POST /trigger | 订阅管理+触发采集 |
| Content | GET /contents | 内容分页列表 |
| Notification | GET /notifications, POST /read | 通知管理 |
| Approval | GET /approvals/pending, POST /approve | 审批流程 |
| System | GET /system/metrics, /charts | 仪表盘数据 |
| Audit | GET /audit-logs | 审计日志 (admin) |

### Python API (`/api/python`)

| 模块 | 端点 | 说明 |
|------|------|------|
| Agent | POST /agent/tasks, GET /tasks/{id}/status | AI 采集任务 |
| Content | GET /contents, POST /{id}/search-similar | 内容+语义搜索 |
| Subscription | GET /subscriptions, POST /{id}/trigger | 订阅管理 |
| Notification | GET /notifications, POST /{id}/read | 通知管理 |

## 数据库设计

6 张业务表：`user` → `subscription` → `content` / `notification` / `approval_ticket` / `audit_log`

![E-R: user 1-N subscription/N notification/N approval/N audit_log; subscription 1-N content]

## 安全设计

- 密码 BCrypt 单向加密存储
- JWT HMAC-SHA256，24 小时过期
- Gateway + Java 双层 JWT 校验
- ThreadLocal UserContext 防止水平越权
- MyBatis-Plus LambdaQueryWrapper 参数绑定防 SQL 注入

## 许可证

MIT
