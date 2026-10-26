# NexusAI 运行与验收说明

## 服务与数据

| 服务 | 默认端口 | 职责 |
|---|---:|---|
| Vite 前端 | 5173 | 浏览器工作台 |
| Spring Cloud Gateway | 8080 | 唯一浏览器 API 入口，JWT 与路由 |
| Java | 8081 | 登录、订阅、通知、审批、统计 |
| Python | 8000 | 采集、任务、内容检索、技能、推送 |
| MySQL | 3306 | 持久化业务数据 |
| Redis | 6379 | 节点热状态投影 |

应用默认绑定本机地址。Java、网关和 Python 使用同一个 `JWT_SECRET`；统一启动脚本读取 `nexus-python/.env` 并传递给子进程。数据库密码、模型密钥与机器人地址不要提交到版本库。

业务表为 `user`、`subscription`、`content`、`approval_ticket`、`notification`、`audit_log`、`agent_task`、`push_channel`、`push_delivery`、`source_health`。`scripts/init_db.py` 创建缺失的表并执行新增字段迁移，不清空已有数据。原有内容正文列会扩展为 LONGTEXT。质量与巡检字段也是增量迁移。`infra/sql/init.sql` 为全新数据库的基线参考，重复初始化请使用 Python 脚本。

数据库会话与应用持久化时间使用 UTC，前端转换为浏览器本地时间。旧版本已写入的历史时间不进行猜测性批量转换。

## 内容获取和解析

- RSS：支持 RSS／Atom，单源最多读取 50 条，保留标题、作者、源链接、发布时间和正文。
- 网页：读取公开静态 HTML，优先提取 article/main，清理脚本、导航和页面噪音；不保证需要登录、验证码或必须运行 JavaScript 的页面。
- JSON API：支持文章数组，以及 `items`、`articles`、`news`、`data` 容器；字段映射支持 `url/link`、`title`、`description/summary/content` 等常见结构。不支持任意私有 API 的认证协议。
- 网络请求最多重试 3 次，限制单响应 4 MB、重定向次数和每订阅最多 20 个源。正常运行禁止访问本机或私有网络地址。
- 原文正文与 `translated_summary` 分开保存。AI 未启用时，界面会明确标识原文或摘录，避免把规则生成结果当成模型输出。
- 当前验收去重为订阅内的源 URL 与清洗内容精确去重。向量语义去重仍是可选扩展代码，不作为当前验收能力。

## 任务和审批

任务状态持久化到 MySQL，Redis 丢失不会丢失审批上下文。`active_key` 唯一约束保证同一订阅只存在一个正在运行的任务。单机任务并发为 3，兼容模式单任务上限为 300 秒，语义模式为 600 秒。

重启时运行中的任务标记为失败并释放占用，可手动重试；待审批任务保留原上下文。失败任务留下的未发布条目可以在重试中复用，避免被去重逻辑永久跳过。此实现不提供任意节点的 LangGraph 原生 checkpoint 回放，也不支持多实例调度。

内容状态：`2=待审`、`1=已发布`、`0=拒绝或不可见`。高风险规则包括大量新内容和敏感关键词；审批通过或拒绝由管理员完成。审批使用条件更新防止重复处理，Java 更新工单后调用 Python 恢复接口。回调失败时工单结果保留，管理员可在任务详情重试恢复。

删除订阅采用软删除，已有已发布内容仍可阅读，采集调度停止。

## 飞书／钉钉推送

1. 在对应群中添加自定义机器人并复制 Webhook。
2. 在工作台的“推送设置”选择平台，填写渠道名称、Webhook 和可选签名密钥。
3. 机器人要求关键词时，可将关键词设置为 `NexusAI`，消息带该前缀。
4. 点击“测试连接”会在确认后向该机器人发送一条测试消息。
5. 新内容发布后投递本次简报；同一次任务与渠道仅建立一条投递记录。失败自动尝试最多 3 次，后续可以手动重试。
6. 若服务在投递中途重启，结果标记为未知失败；先确认群消息是否已收到，再决定重试，避免重复通知。

投递配置接口不会返回 Webhook 或签名密钥。当前版本在本地数据库保存机器人配置，应控制数据库访问权限。

协议参考：[飞书自定义机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)、[钉钉自定义机器人](https://open.dingtalk.com/document/robots/custom-robot-access)。

## 自动化回归

单元测试：

```powershell
python -m pip install -r nexus-python/requirements-dev.txt
# Windows 上若全局 pytest 插件干扰，可设置此变量：
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest
```

业务端到端测试使用本地 RSS、网页和机器人模拟服务，不向真实群发送消息。它需要一个已获授权的测试审核账号；脚本不会创建或提升管理员权限。

```powershell
python scripts/dev.py stop
$env:NEXUS_ALLOW_LOCAL_SOURCES='true'
python scripts/dev.py start --build
$env:E2E_ADMIN_USER='你的测试审核账号'
$env:E2E_ADMIN_PASSWORD='该账号密码'
python scripts/e2e.py

# 测试后恢复正常网络约束：
python scripts/dev.py stop
Remove-Item Env:NEXUS_ALLOW_LOCAL_SOURCES
Remove-Item Env:E2E_ADMIN_USER
Remove-Item Env:E2E_ADMIN_PASSWORD
python scripts/dev.py start
```

测试账号、任务和模拟内容使用 `e2e_` 前缀，与真实用户数据区分。测试结果保存在 `.runtime/e2e-result.json`。浏览器验收脚本为 `scripts/browser_check.py`，截图保存在 `.runtime`。

浏览器验收前执行 `python -m playwright install chromium`，然后运行 `python scripts/browser_check.py`。本轮已完成的检查和能力边界见 [验证记录](VERIFICATION.md)。

来源健康维护与试采说明见 [数据源文档](SOURCES.md)。`scripts/quality_trial_check.py` 用普通临时账号验证只读试采、正文质量、实际入库和浏览器；需要先按上文设置 `NEXUS_ALLOW_LOCAL_SOURCES=true`，同时设置 `SOURCE_HEALTH_ENABLED=false`，再重启应用。结束后恢复前者为 false、后者为 true 并重启。脚本不需要管理员，也不会向真实群发送消息。

## 已知边界

- 本次完成的是本机单实例运行，尚未验证生产集群、故障转移或大规模负载。
- 外部站点的可访问性和内容结构会变化；单源失败可在任务详情查看，不会伪造成功结果。
- AI 与真实群投递依赖用户自己的服务配置；不把未配置能力显示为已成功执行。
- RocketMQ、Milvus、旧版面试材料中的 Nacos／SQL Server／原生 checkpoint 等不属于本轮已验证主链路。

自动来源验收可在正常配置运行 `python scripts/auto_sources_check.py`。它使用普通临时账号验证无 URL 创建、来源标记、用户来源保留、排除、任务刷新及浏览器操作；结束后暂停测试订阅，不需要管理员或真实机器人。

语义订阅默认在新建界面启用，需要模型配置。试采、成本预算、失败保护、真实模型小样本评估与全栈验收命令见 [语义订阅说明](SEMANTIC.md)。
