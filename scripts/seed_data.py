"""向数据库插入丰富的示例数据，用于课程报告截图"""
import pymysql
import uuid
import random
from datetime import datetime, timedelta

conn = pymysql.connect(
    host='localhost', user='root', password='712693',
    database='nexusai', charset='utf8mb4'
)
cur = conn.cursor()

now = datetime.now()

# =============================================
# 1. 新增用户
# =============================================
users_to_add = [
    (3, 'admin', 'admin', now - timedelta(days=30)),
    (4, 'zhangsan', 'user', now - timedelta(days=20)),
    (5, 'wangwu', 'user', now - timedelta(days=15)),
    (6, 'lisi', 'user', now - timedelta(days=10)),
]
for uid, uname, role, ts in users_to_add:
    cur.execute(
        "INSERT IGNORE INTO user (id, username, password_hash, email, role, created_at) "
        "VALUES (%s, %s, '$2a$10$placeholder_hash_here', %s, %s, %s)",
        (uid, uname, f'{uname}@nexusai.com', role, ts)
    )

# =============================================
# 2. 新增订阅（多样化）
# =============================================
new_subs = [
    (7, 2, 'GitHub Trending', '["https://rsshub.app/github/trending/daily"]', '["rss"]'),
    (8, 2, 'V2EX 技术', '["https://rsshub.app/v2ex/topics/tech"]', '["rss"]'),
    (9, 3, '产品经理日报', '["https://rsshub.app/pmcafe/today"]', '["rss"]'),
    (10, 3, '36氪快讯', '["https://rsshub.app/36kr/newsflashes"]', '["rss"]'),
    (11, 4, '知乎热榜', '["https://rsshub.app/zhihu/hotlist"]', '["rss"]'),
    (12, 4, '微博热搜', '["https://rsshub.app/weibo/search/hot"]', '["web"]'),
    (13, 5, '开发者头条', '["https://rsshub.app/toutiao/today"]', '["rss"]'),
    (14, 6, 'B站热门', '["https://rsshub.app/bilibili/hot-search"]', '["web"]'),
]
for sid, uid, name, kw, sp in new_subs:
    cur.execute(
        "INSERT INTO subscription (id, user_id, name, keywords, source_platforms, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s, 1, %s)",
        (sid, uid, name, kw, sp, now - timedelta(days=random.randint(1, 20)))
    )

# =============================================
# 3. 新增内容（24小时分散，多平台）
# =============================================
platforms_content = {
    'rss': [
        ('RSSHub 架构设计与实践指南', '本文详细介绍了 RSSHub 的微服务架构设计，包括路由系统、缓存策略和插件机制。RSSHub 是一个开源的 RSS 聚合工具，可以将各种网站的内容转换为标准 RSS 格式。', 'DIYgod', 'https://rsshub.app/blog/architecture'),
        ('深度学习在自然语言处理中的最新进展', '2024年NLP领域取得了显著突破，大语言模型在各行各业广泛应用。本文将综述最新的Transformer变体、提示工程技术和模型压缩方法。', '张明', 'https://example.com/nlp-2024'),
        ('React 19 新特性解读：Server Components', 'React 19正式版终于发布了，其中最受瞩目的Server Components让前端渲染方式发生了革命性变化。本文详细解析RSC的工作原理和最佳实践。', '李华', 'https://example.com/react-19-rsc'),
        ('Flutter 3.22 发布：支持 WebAssembly', 'Google发布了Flutter 3.22版本，新增对WebAssembly的原生支持，同时改进了Material Design 3组件和性能优化工具。', '王磊', 'https://example.com/flutter-3-22'),
        ('Kubernetes 1.30 版本更新盘点', 'K8s 1.30带来了多项重要更新：Sidecar容器正式GA、改进的Pod安全策略、以及更高效的调度算法。', '陈工', 'https://example.com/k8s-1-30'),
        ('TypeScript 5.5 类型系统增强', '微软发布了TypeScript 5.5，引入新的类型推断算法，大幅减少了对类型注解的依赖。同时改进了编辑器性能和错误提示。', '赵鹏', 'https://example.com/ts-5-5'),
        ('Rust 在嵌入式系统中的应用趋势', '越来越多的嵌入式开发者选择Rust语言，其内存安全特性成为关键考量。本文分析了Rust在IoT设备、汽车电子等领域的应用案例。', '刘博', 'https://example.com/rust-embedded'),
        ('大模型应用落地的三个关键挑战', '企业在部署大语言模型时面临的挑战包括：推理成本控制、幻觉问题缓解、以及领域知识注入。本文给出实用的解决方案。', '周教授', 'https://example.com/llm-challenges'),
        ('PostgreSQL 17 性能优化实战', 'PostgreSQL 17引入了并行查询改进和增量备份功能。本文通过实际案例展示如何利用这些特性提升数据库性能。', 'DBA小组', 'https://example.com/pg-17-perf'),
        ('前端性能优化：从LCP 5s到1s的实践之路', '通过代码分割、图片优化、CDN加速和预加载策略，将一个电商网站的LCP从5秒降至1秒以内。', '前端团队', 'https://example.com/lcp-optimization'),
        ('Go语言错误处理的最佳实践', 'Go 1.22改进了错误处理机制，本文总结了在实际项目中处理错误的常见模式和反模式。', '老K', 'https://example.com/go-error-handling'),
        ('Elasticsearch 8.x 搜索优化技巧', '总结了ES 8.x中10个实用的搜索性能优化技巧，包括索引设计、查询优化和集群配置调整。', '搜索团队', 'https://example.com/es8-tips'),
    ],
    'web': [
        ('2024中国人工智能产业发展白皮书', '中国信通院发布最新AI产业白皮书，预计2024年中国AI产业规模将突破6000亿元。报告涵盖了基础层、技术层和应用层的全景分析。', '信通院', 'https://example.com/ai-white-paper'),
        ('数字化办公转型调查报告', '超过80%的企业已将数字化办公纳入战略规划，但仅30%实现了有效落地。报告分析了主要障碍和成功因素。', '麦肯锡', 'https://example.com/digital-office'),
        ('全球网络安全态势分析周报', '本周全球网络安全事件：勒索软件攻击增长30%，供应链攻击成为新的主要威胁向量。', '安恒信息', 'https://example.com/security-weekly'),
        ('云计算市场格局变化：阿里云vs华为云', '两大云厂商最新季度财报对比分析，在AI算力市场的争夺战中各显神通。', '云计算频道', 'https://example.com/cloud-market'),
        ('智能驾驶年度评测报告发布', '10款主流车型的智能驾驶系统横评，涵盖高速NOA、城市CNOA和自动泊车三大场景。', '汽车之家', 'https://example.com/auto-drive'),
        ('区块链在供应链金融中的落地案例', '某大型制造企业运用区块链技术改造供应链金融，将融资审批时间从7天缩短至1天。', '金融科技', 'https://example.com/blockchain-fin'),
    ],
    'AI': [
        ('基于注意力机制的时序预测模型综述', '本文全面综述了Transformer及其变体在时间序列预测中的应用，包括PatchTST、iTransformer等最新模型。', 'AI研究院', 'https://example.com/attention-timeseries'),
        ('多模态大模型的幻觉问题与缓解策略', '系统性地分析了多模态大模型产生幻觉的原因，并从数据、训练和推理三个层面提出了缓解方案。', '刘研究员', 'https://example.com/multimodal-hallucination'),
        ('基于强化学习的自动化代码审查系统', '利用RLHF训练的代码审查模型在多个开源项目上达到了人类审查者85%的准确率。', '赵博士', 'https://example.com/rl-code-review'),
        ('知识图谱增强的检索增强生成系统', '将知识图谱与RAG结合，显著提升了问答系统的事实准确性，在医疗和法律领域表现突出。', '创新团队', 'https://example.com/kg-rag'),
    ],
}

all_content = []
for platform, items in platforms_content.items():
    for title, summary, author, url in items:
        all_content.append((platform, title, summary, author, url))

# 将时间分散到过去24小时
random.shuffle(all_content)
for i, (platform, title, summary, author, url) in enumerate(all_content):
    hours_ago = random.uniform(0, 23)
    ts = now - timedelta(hours=hours_ago)
    cid = str(uuid.uuid4())
    c_hash = str(uuid.uuid4())[:12]  # simplified hash
    cur.execute(
        "INSERT INTO content (id, subscription_id, source_platform, source_url, title, summary, "
        "author, content_hash, status, is_duplicate, fetched_at, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 0, %s, %s)",
        (cid, random.choice([2,3,4,5,6,7,8,9,10,11,12,13,14]), platform, url,
         title, summary, author, c_hash, ts, ts)
    )

# =============================================
# 4. 审批工单（pending/approved/rejected）
# =============================================
approval_data = [
    ('60a1b2c3-d4e5-4f67-8901-234567890001', 3, 'trigger_collection', 1,
     '{"subscription_id": 9, "target": "产品经理日报"}', 0, None, None, None, now - timedelta(hours=2)),
    ('60a1b2c3-d4e5-4f67-8901-234567890002', 4, 'trigger_collection', 1,
     '{"subscription_id": 11, "target": "知乎热榜"}', 0, None, None, None, now - timedelta(hours=5)),
    ('60a1b2c3-d4e5-4f67-8901-234567890003', 5, 'delete_content', 2,
     '{"content_id": "abc123", "reason": "内容已过时"}', 0, None, None, None, now - timedelta(hours=8)),
    ('60a1b2c3-d4e5-4f67-8901-234567890004', 3, 'modify_subscription', 1,
     '{"subscription_id": 10, "changes": {"name": "36氪快讯V2"}}', 1, 2, now - timedelta(hours=3), '修改通过，名称更新已生效', now - timedelta(hours=4)),
    ('60a1b2c3-d4e5-4f67-8901-234567890005', 4, 'export_data', 2,
     '{"format": "csv", "date_range": "2026-05"}', 1, 2, now - timedelta(hours=6), '数据导出权限审批通过', now - timedelta(hours=7)),
    ('60a1b2c3-d4e5-4f67-8901-234567890006', 5, 'delete_content', 2,
     '{"content_id": "def456", "reason": "版权问题"}', 2, 2, now - timedelta(hours=10), '涉及版权，已拒绝删除请求', now - timedelta(hours=9)),
    ('60a1b2c3-d4e5-4f67-8901-234567890007', 6, 'trigger_collection', 1,
     '{"subscription_id": 14, "target": "B站热门"}', 1, 2, now - timedelta(hours=1), '已批准，任务已加入队列', now - timedelta(hours=12)),
    ('60a1b2c3-d4e5-4f67-8901-234567890008', 3, 'system_config', 3,
     '{"config_key": "max_concurrent_tasks", "value": 10}', 2, 2, now - timedelta(days=1), '高风险配置变更需更高权限审批', now - timedelta(days=2)),
]
for task_id, uid, action, risk, ctx, status, approved_by, approved_at, comment, created_at in approval_data:
    cur.execute(
        "INSERT INTO approval_ticket (task_id, user_id, action_type, risk_level, context, status, "
        "approved_by, approved_at, comment, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (task_id, uid, action, risk, ctx, status, approved_by, approved_at, comment, created_at)
    )

# =============================================
# 5. 通知
# =============================================
notifications = [
    (2, 'task', '采集完成: AI资讯', '从 Hacker News 新增 15 条内容', 0, 'task-001', now - timedelta(hours=1)),
    (2, 'task', '采集完成: The Verge', '从 The Verge 新增 8 条内容', 0, 'task-002', now - timedelta(hours=3)),
    (2, 'system', '系统升级通知', '系统将于本周六凌晨2点-4点进行维护升级', 1, None, now - timedelta(hours=5)),
    (2, 'approval', '审批结果: 数据导出', '您的数据导出申请已通过，请在下载中心获取文件', 0, 'ticket-005', now - timedelta(hours=6)),
    (3, 'task', '采集完成: 产品经理日报', '新增 6 条内容', 1, 'task-003', now - timedelta(hours=4)),
    (3, 'approval', '审批请求: 修改订阅', '用户 zhangsan 申请修改订阅规则，请审批', 0, 'ticket-004', now - timedelta(hours=4)),
    (3, 'system', '安全提醒', '检测到您的账号在陌生设备登录，如非本人操作请立即修改密码', 0, None, now - timedelta(hours=12)),
    (4, 'task', '采集完成: 知乎热榜', '新增 12 条内容', 0, 'task-004', now - timedelta(hours=2)),
    (4, 'task', '采集失败: 微博热搜', 'RSSHub 实例连接超时，请检查网络或更换源地址', 0, 'task-005', now - timedelta(hours=7)),
    (4, 'approval', '审批结果: 触发采集', '您的采集任务申请已通过，任务正在执行中', 1, 'ticket-007', now - timedelta(hours=1)),
    (5, 'task', '采集完成: 开发者头条', '新增 5 条内容', 1, 'task-006', now - timedelta(days=1)),
    (6, 'system', '欢迎加入 NexusAI', '欢迎使用 NexusAI 智能内容采集系统，开始您的第一条订阅吧！', 1, None, now - timedelta(days=9)),
    (6, 'task', '采集完成: B站热门', '新增 20 条内容', 0, 'task-007', now - timedelta(hours=1)),
]
for uid, ntype, title, content, is_read, rel_id, ts in notifications:
    cur.execute(
        "INSERT INTO notification (user_id, type, title, content, is_read, related_id, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (uid, ntype, title, content, is_read, rel_id, ts)
    )

# =============================================
# 6. 审计日志
# =============================================
audit_logs = [
    (2, 'LOGIN', 'user', '2', now - timedelta(hours=1), '192.168.1.100', 'req-001'),
    (2, 'CREATE_SUB', 'subscription', '7', now - timedelta(hours=2), '192.168.1.100', 'req-002'),
    (2, 'TRIGGER_COLLECTION', 'subscription', '2', now - timedelta(hours=3), '192.168.1.100', 'req-003'),
    (2, 'LOGOUT', 'user', '2', now - timedelta(hours=4), '192.168.1.100', 'req-004'),
    (3, 'LOGIN', 'user', '3', now - timedelta(hours=5), '10.0.0.55', 'req-005'),
    (3, 'CREATE_SUB', 'subscription', '9', now - timedelta(hours=6), '10.0.0.55', 'req-006'),
    (4, 'LOGIN', 'user', '4', now - timedelta(hours=2), '172.16.0.20', 'req-007'),
    (4, 'VIEW_CONTENT', 'content', 'abc', now - timedelta(hours=2, minutes=30), '172.16.0.20', 'req-008'),
    (5, 'LOGIN', 'user', '5', now - timedelta(hours=7), '192.168.2.88', 'req-009'),
    (5, 'DELETE_CONTENT', 'content', 'def', now - timedelta(hours=8), '192.168.2.88', 'req-010'),
    (6, 'LOGIN', 'user', '6', now - timedelta(hours=1), '10.10.10.10', 'req-011'),
    (6, 'CREATE_SUB', 'subscription', '14', now - timedelta(hours=9), '10.10.10.10', 'req-012'),
    (2, 'MARK_NOTIFICATION_READ', 'notification', '2', now - timedelta(hours=1, minutes=30), '192.168.1.100', 'req-013'),
    (3, 'APPROVE_TICKET', 'approval_ticket', '1', now - timedelta(hours=3), '10.0.0.55', 'req-014'),
    (2, 'LOGIN', 'user', '2', now - timedelta(hours=10), '192.168.1.100', 'req-015'),
]
for uid, action, target_type, target_id, ts, ip, req_id in audit_logs:
    cur.execute(
        "INSERT INTO audit_log (user_id, action, target_type, target_id, action_time, ip_address, request_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (uid, action, target_type, target_id, ts, ip, req_id)
    )

conn.commit()
print("Seed data inserted successfully!")
print(f"  users: {cur.execute('SELECT COUNT(*) FROM user').fetchone()[0]}")
print(f"  subscriptions: {cur.execute('SELECT COUNT(*) FROM subscription').fetchone()[0]}")
print(f"  content: {cur.execute('SELECT COUNT(*) FROM content').fetchone()[0]}")
print(f"  approval_tickets: {cur.execute('SELECT COUNT(*) FROM approval_ticket').fetchone()[0]}")
print(f"  notifications: {cur.execute('SELECT COUNT(*) FROM notification').fetchone()[0]}")
print(f"  audit_logs: {cur.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0]}")

# Show platform distribution
cur.execute('SELECT source_platform, COUNT(*) FROM content GROUP BY source_platform')
print("\nPlatform distribution:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Show hourly distribution
cur.execute("""
    SELECT DATE_FORMAT(fetched_at, '%Y-%m-%d %H:00'), COUNT(*)
    FROM content WHERE fetched_at IS NOT NULL
    GROUP BY DATE_FORMAT(fetched_at, '%Y-%m-%d %H')
    ORDER BY 1
""")
print("\nHourly trend:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
