# NexusAI 项目实现细节文档

> 生成时间：2026-06-05 | 基于当前代码库完整扫描

---

## 1. 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (React :5173)                     │
│               Ant Design 5 + Zustand + ECharts                │
└──────────────────────────┬───────────────────────────────────┘
                           │ /api/*
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               Gateway (Spring Cloud :8080)                    │
│          JWT校验 | 路由分发 | CORS | RequestId                │
└───────────────┬──────────────────────────┬───────────────────┘
                │ /api/java/**             │ /api/python/**
                ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────────┐
│  Java Backend (:8081)     │  │   Python Backend (:8000)       │
│  Spring Boot 3.2.5        │  │   FastAPI + LangGraph          │
│  MyBatis-Plus + JWT       │◄─┤   Scout Agent + MCP            │
│  CRUD + Auth + 审批        │  │   翻译 + 抓取 + 去重            │
└───────────┬───────────────┘  └──────────┬────────────────────┘
            │                              │
            ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│   MySQL 8.0 (:3306)  │    │  Redis │ Milvus │ RocketMQ         │
│   6 张业务表          │    │  (锁)  │ (去重) │ (消息)           │
└──────────────────────┘    └──────────────────────────────────┘
```

---

## 2. 数据库设计 (MySQL 8.0)

### 2.1 表结构

#### user（用户表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK AUTO_INCREMENT | 用户ID |
| username | VARCHAR(50) | UNIQUE NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | BCrypt 密文 |
| email | VARCHAR(100) | - | 邮箱 |
| role | VARCHAR(20) | DEFAULT 'user' | admin / user |
| created_at | DATETIME | DEFAULT NOW() | 创建时间 |

#### subscription（订阅规则表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK AUTO_INCREMENT | 规则ID |
| user_id | BIGINT | FK→user.id | 所属用户 |
| name | VARCHAR(100) | NOT NULL | 规则名称 |
| keywords | JSON | - | 订阅源URL/RSS地址数组 |
| source_platforms | JSON | - | 平台数组: rss/web/AI |
| match_mode | TINYINT | DEFAULT 1 | 1=精确 2=模糊 3=语义 |
| trigger_conditions | JSON | - | 触发条件配置 |
| priority | TINYINT | DEFAULT 2 | 1=高 2=中 3=低 |
| status | TINYINT | DEFAULT 1 | 0=暂停 1=启用 |
| cron_expression | VARCHAR(100) | - | 定时表达式 |
| last_run_at | DATETIME | - | 上次执行时间 |
| created_at / updated_at | DATETIME | - | 时间戳 |

#### content（内容表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PK | UUID v4 (应用层生成) |
| subscription_id | BIGINT | FK→subscription.id | 来源订阅 |
| source_platform | VARCHAR(32) | - | rss / web / AI |
| source_url | VARCHAR(1000) | - | 原文链接 |
| title | VARCHAR(500) | - | 标题 |
| summary | TEXT | - | 摘要 |
| content_body | LONGTEXT | - | 正文 HTML |
| author | VARCHAR(100) | - | 作者 |
| published_at | DATETIME | - | 发布时间 |
| fetched_at | DATETIME | DEFAULT NOW() | 采集时间 |
| content_hash | CHAR(64) | UNIQUE | SHA-256 (用于去重) |
| vector_id | VARCHAR(64) | - | Milvus 向量ID |
| status | TINYINT | DEFAULT 1 | 1=有效 |
| is_duplicate | TINYINT | DEFAULT 0 | 0=否 1=是 |
| duplicate_of | CHAR(36) | - | 指向重复源 |
| related_contents | JSON | - | 关联内容ID数组 |
| created_at | DATETIME | DEFAULT NOW() | 创建时间 |

**索引**：(subscription_id), (content_hash), (source_platform, is_duplicate)

#### approval_ticket（审批工单表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK AUTO_INCREMENT | 工单ID |
| task_id | VARCHAR(64) | NOT NULL | 关联任务ID |
| user_id | BIGINT | FK→user.id | 申请人 |
| action_type | VARCHAR(50) | - | trigger_collection / delete_content / modify_subscription / export_data / system_config |
| risk_level | TINYINT | CHECK 1-3 | 1=低 2=中 3=高 |
| context | JSON | - | 业务上下文 |
| status | TINYINT | DEFAULT 0 | 0=待审批 1=已通过 2=已拒绝 |
| approved_by | BIGINT | FK→user.id | 审批人 |
| approved_at | DATETIME | - | 审批时间 |
| comment | VARCHAR(500) | - | 审批意见 |
| created_at | DATETIME | DEFAULT NOW() | 创建时间 |

#### notification（通知表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK AUTO_INCREMENT | 通知ID |
| user_id | BIGINT | FK→user.id | 接收用户 |
| type | VARCHAR(50) | NOT NULL | task / system / approval |
| title | VARCHAR(200) | NOT NULL | 通知标题 |
| content | TEXT | - | 通知内容 |
| is_read | TINYINT | DEFAULT 0 | 0=未读 1=已读 |
| related_id | VARCHAR(64) | - | 关联业务ID |
| created_at | DATETIME | DEFAULT NOW() | 创建时间 |

**索引**：(user_id, is_read)

#### audit_log（审计日志表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK AUTO_INCREMENT | 日志ID |
| user_id | BIGINT | - | 操作用户 |
| action | VARCHAR(50) | NOT NULL | 操作类型 |
| target_type | VARCHAR(50) | - | 目标类型 |
| target_id | VARCHAR(64) | - | 目标ID |
| action_time | DATETIME | DEFAULT NOW() | 操作时间 |
| ip_address | VARCHAR(64) | - | IP地址 |
| request_id | VARCHAR(64) | - | 请求追踪ID |

**索引**：(action_time DESC)

### 2.2 E-R 关系

```
user (1) ─────< (N) subscription
user (1) ─────< (N) notification
user (1) ─────< (N) approval_ticket (申请人)
user (1) ─────< (N) approval_ticket (审批人)
user (1) ─────< (N) audit_log
subscription (1) ──< (N) content
```

---

## 3. 后端 API 清单

### 3.1 Java Backend (Spring Boot, :8081)

所有 Java API 路径前缀 `/api/java`，Gateway 路由后对外暴露。

#### Auth 模块 — `/api/java/auth`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /register | 公开 | 注册，BCrypt 加密密码 |
| POST | /login | 公开 | 登录，返回 JWT + 用户信息 |

**登录响应格式**：
```json
{
  "code": 200,
  "data": {
    "token": "eyJ...",
    "tokenType": "Bearer",
    "expiresIn": 86400,
    "user": { "id": 1, "username": "test", "role": "user" }
  }
}
```

#### Subscription 模块 — `/api/java/subscriptions`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | / | user | 创建订阅规则 |
| PUT | /{id} | user(本人) | 更新订阅规则 |
| DELETE | /{id} | user(本人) | 删除订阅规则 |
| GET | /{id} | user | 订阅详情 |
| GET | / | user | 分页列表（支持 name/status 筛选） |
| POST | /{id}/trigger | user(本人) | 手动触发采集 |

**创建请求体**：
```json
{
  "name": "AI资讯",
  "keywords": ["https://hnrss.org/frontpage"],
  "sourcePlatforms": ["rss"],
  "matchMode": 1,
  "priority": 2
}
```

#### Content 模块 — `/api/java/contents`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | / | user | 分页列表（支持 subscriptionId 筛选） |
| GET | /{id} | user | 内容详情（含关联订阅名） |

**列表响应**：IPage\<ContentVO\>，`records` 字段为数据数组。

#### Notification 模块 — `/api/java/notifications`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | / | user(本人) | 分页通知列表 |
| GET | /unread-count | user(本人) | 未读计数 |
| POST | /{id}/read | user(本人) | 标记单条已读 |
| POST | /read-all | user(本人) | 全部标记已读 |

#### Approval 模块 — `/api/java/approvals`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /pending | admin | 待审批列表（status=0） |
| GET | /{id} | admin | 工单详情 |
| POST | /{id}/approve | admin | 通过 |
| POST | /{id}/reject | admin | 拒绝 |

**审批请求体**：`{ "approvedBy": 2, "comment": "同意" }`

#### System 模块 — `/api/java/system`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /health | 公开 | "ok" |
| GET | /metrics | user | 4项统计数（用户/订阅/内容/待审批） |
| GET | /charts | user | 平台分布 + 24小时趋势 |

**charts 响应格式**：
```json
{
  "platformDistribution": [{"platform": "rss", "count": 59}],
  "hourlyTrend": [{"hour": "2026-06-05 10:00", "count": 5}]
}
```

#### Audit Log 模块 — `/api/java/audit-logs`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | / | admin | 分页审计日志列表 |

---

### 3.2 Python Backend (FastAPI, :8000)

所有 Python API 路径前缀 `/api/python`。

#### Agent — `/api/python/agent`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| POST | /tasks | subscription_id (query) | 触发 Scout Agent 采集 |
| GET | /tasks/{task_id}/status | - | 查询任务状态 (Redis) |

#### Content — `/api/python/contents`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 分页列表 |
| GET | /{id} | 详情 |
| POST | /{id}/search-similar | Milvus 语义相似搜索 |

#### Subscription — `/api/python/subscriptions`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 分页列表 |
| GET | /{id} | 详情 |
| POST | /{id}/trigger | 触发采集 |

#### Notification — `/api/python/notifications`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 分页列表（按 user_id） |
| POST | /{id}/read | 标记已读 |

---

## 4. 核心业务流程

### 4.1 内容采集流水线

```
用户点击"触发采集"
    │
    ▼
Java SubscriptionServiceImpl.trigger()
    ├─ Redis 分布式锁 (lock:collection:{subId}, 5min TTL)
    ├─ RocketMQ 发送 TaskTriggerMessage ──┐ (不可用时走 HTTP fallback)
    │                                      │
    ▼                                      ▼
Python Scout Agent                    HTTP POST /api/python/agent/tasks
    │
    ├─ Step 1: feedparser 解析 RSS
    │     └─ 提取: title, summary, author, link, published_at
    │
    ├─ Step 2: 元数据检测 (_is_metadata_only)
    │     └─ 检测 HN 风格的 "Article URL: ..." 摘要
    │     └─ 如果纯元数据 → httpx + BeautifulSoup 抓取原文正文
    │
    ├─ Step 3: 翻译 (_translate_to_chinese)
    │     └─ 检测非中文 (>85% 非 CJK) → LLM 翻译为中文
    │     └─ API key 为空则跳过
    │
    ├─ Step 4: 去重 (content_hash SHA-256)
    │     └─ 查询 content 表 content_hash 列
    │
    ├─ Step 5: 存储
    │     └─ INSERT INTO content (UUID id, ...)
    │     └─ Milvus insert (可选)
    │
    └─ Step 6: 通知
          └─ INSERT INTO notification (user_id, type='task', ...)
```

### 4.2 认证流程

```
登录请求 (username + password)
    │
    ▼
AuthServiceImpl.login()
    ├─ 查 user 表
    ├─ BCrypt.matches(password, password_hash)
    └─ JwtUtil.generateToken(userId, username, role)
          └─ 签发 24h 有效 JWT

后续请求:
    ├─ Gateway JwtGlobalFilter 校验 JWT → 注入 X-User-Id/X-Username/X-Role
    └─ Java JwtAuthenticationInterceptor 再次校验 → UserContext (ThreadLocal)
          └─ 业务代码通过 UserContext.getUserId() 获取当前用户
```

### 4.3 水平越权防护

```java
// ❌ 修复前 — 从请求参数取 userId，可被篡改
public Result<Void> delete(@RequestParam Long userId, @PathVariable Long id) {
    subscriptionService.delete(userId, id);
}

// ✅ 修复后 — 从 ThreadLocal 取当前认证用户
public Result<Void> delete(@PathVariable Long id) {
    Long userId = UserContext.getUserId();
    subscriptionService.delete(userId, id);
}
```

---

## 5. 前端页面清单

| 路由 | 页面 | 组件 | 调用的API |
|------|------|------|-----------|
| /login | 登录/注册 | Tabs + Form | POST /auth/login, /auth/register |
| /dashboard | 仪表盘 | 4×Statistic卡片 + ECharts饼图+折线图 | GET /system/metrics, /charts |
| /subscriptions | 订阅管理 | Table + Modal(创建/编辑) + 触发/删除按钮 | GET/POST/PUT/DELETE /subscriptions, /trigger |
| /contents | 内容中心 | Table(可展开行) + 搜索 | GET /contents |
| /approvals | 审批工单 | Table + 通过/拒绝按钮 | GET /approvals/pending, POST /approve, /reject |
| /notifications | 通知中心 | Table + 标记已读/全部已读 | GET /notifications, POST /read, /read-all |

**布局**：左侧 200px Sider（5个菜单项）+ 顶部 Header（用户名+退出下拉菜单）

**状态管理** (Zustand + persist)：
```typescript
auth: { token, user: { id, username, role }, isAdmin() }
// 持久化到 localStorage key "nexus-auth"
```

---

## 6. 安全设计

| 机制 | 实现 | 位置 |
|------|------|------|
| 密码加密 | BCrypt (spring-security-crypto) | AuthServiceImpl |
| 身份认证 | JWT HMAC-SHA256, 24h 过期 | JwtUtil + JwtAuthenticationInterceptor + JwtGlobalFilter |
| 水平越权防护 | UserContext (ThreadLocal) 替代 @RequestParam userId | JwtAuthenticationInterceptor |
| 垂直权限 | role="admin" 判断 | Approval/Audit Controller |
| SQL注入防护 | MyBatis-Plus LambdaQueryWrapper (参数绑定) | 所有 ServiceImpl |
| CSRF | JWT Bearer Token (无Cookie) | — |
| 请求追踪 | X-Request-Id 全链路透传 | RequestIdFilter (Java) + RequestIdGatewayFilter |

---

## 7. 配置速查

### Java (application.yml)
```yaml
server.port: 8081
spring.datasource: mysql://localhost:3306/nexusai (root/712693)
spring.redis: localhost:6379
rocketmq.enabled: false  # 本地开发关闭
jwt.secret: nexus-ai-secret-key-2026
jwt.expiration: 86400000  # 24h
```

### Python (config.py)
```python
LLM_API_KEY=""  # 翻译功能需要配置
DB_HOST=localhost, DB_PORT=3306, DB_PASSWORD=712693
REDIS_HOST=localhost, REDIS_PORT=6379
MILVUS_HOST=localhost, MILVUS_PORT=19530
```

### Gateway (application.yml)
```yaml
server.port: 8080
routes:
  /api/java/** → localhost:8081
  /api/python/** → localhost:8000
cors: allowedOriginPatterns: "*"
```

### Frontend (vite.config.ts)
```typescript
proxy: { '/api': { target: 'http://localhost:8080' } }
port: 5173
```

---

## 8. 本地启动顺序

```
1. MySQL 8.0 (localhost:3306, root/712693, database: nexusai)
2. Redis (localhost:6379)
3. Java:   cd nexus-java && mvn spring-boot:run           → :8081
4. Python: cd nexus-python && uvicorn app.main:app --reload → :8000
5. Gateway: cd gateway && mvn spring-boot:run              → :8080
6. Frontend: cd frontend && npm run dev                     → :5173
```

浏览器访问 `http://localhost:5173`

---

## 9. 已知设计边界

| 项目 | 状态 | 说明 |
|------|------|------|
| RocketMQ | 本地关闭 | `rocketmq.enabled=false`，Java 用 HTTP fallback 调 Python |
| Milvus | 本地关闭 | 去重降级为 content_hash 查 MySQL |
| 审批工单创建 | 未实现 | Actor Agent (Phase 2) — Python 端高风险操作用 |
| 定时采集 | 未实现 | cron_expression 字段已预留，缺少调度器 |
| 邮件通知 | 代码已就绪 | MCP email server 已配置，缺少 SMTP 凭据 |
| 语义搜索 | 依赖 Milvus | Python content API 已预留端点 |
