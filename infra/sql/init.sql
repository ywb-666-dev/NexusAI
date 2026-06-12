

CREATE DATABASE IF NOT EXISTS nexusai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE nexusai;

CREATE TABLE IF NOT EXISTS `user` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    `role` VARCHAR(20) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    keywords JSON,
    source_platforms JSON,
    match_mode TINYINT DEFAULT 1 COMMENT '1=精确 2=模糊 3=语义',
    trigger_conditions JSON,
    priority TINYINT DEFAULT 2 COMMENT '1=高 2=中 3=低',
    `status` TINYINT DEFAULT 1 COMMENT '0=暂停 1=启用',
    cron_expression VARCHAR(100),
    last_run_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    INDEX idx_subscription_user_status (user_id, `status`)
);

CREATE TABLE IF NOT EXISTS content (
    id CHAR(36) PRIMARY KEY,
    subscription_id BIGINT NOT NULL,
    source_platform VARCHAR(32) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    summary TEXT,
    content_body LONGTEXT,
    author VARCHAR(100),
    published_at DATETIME,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_hash CHAR(64) NOT NULL UNIQUE,
    vector_id VARCHAR(64),
    `status` TINYINT DEFAULT 1 COMMENT '0=删除 1=有效',
    is_duplicate TINYINT DEFAULT 0 COMMENT '0=正常 1=重复',
    duplicate_of CHAR(36) NULL,
    related_contents JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_content_subscription (subscription_id),
    INDEX idx_content_hash (content_hash),
    INDEX idx_content_platform_duplicate (source_platform, is_duplicate)
);

CREATE TABLE IF NOT EXISTS approval_ticket (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    action_type VARCHAR(50),
    risk_level TINYINT CHECK (risk_level IN (1,2,3)),
    context JSON,
    `status` TINYINT DEFAULT 0 COMMENT '0=待审批 1=通过 2=拒绝',
    approved_by BIGINT NULL,
    approved_at DATETIME NULL,
    comment VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    `action` VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(64),
    action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(64),
    request_id VARCHAR(64),
    INDEX idx_audit_time (action_time DESC)
);

CREATE TABLE IF NOT EXISTS notification (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    `type` VARCHAR(50) NOT NULL COMMENT 'task/approval/system',
    title VARCHAR(200) NOT NULL,
    content TEXT,
    is_read TINYINT DEFAULT 0,
    related_id VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notification_user_read (user_id, is_read)
);


-- 用户（密码均为 admin123 的 bcrypt 哈希）
INSERT INTO `user` (id, username, password_hash, email, `role`) VALUES
(1, 'admin',    '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'admin@nexusai.com',   'admin'),
(2, 'zhangsan', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'zhangsan@example.com', 'user'),
(3, 'lisi',     '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'lisi@example.com',     'user'),
(4, 'wangwu',   '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'wangwu@example.com',   'user'),
(5, 'editor01', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'editor01@example.com', 'user');

-- 订阅规则
INSERT INTO subscription (id, user_id, name, keywords, source_platforms, match_mode, priority, `status`, cron_expression) VALUES
(1, 1, 'AI技术前沿',     '["https://hnrss.org/frontpage", "AI technology"]',              '["rss", "api"]',       2, 1, 1, '0 */2 * * *'),
(2, 1, '开源项目监控',   '["https://github.com/trending", "open source"]',                 '["rss", "web"]',       1, 2, 1, '0 */4 * * *'),
(3, 2, '数据科学资讯',   '["https://www.kdnuggets.com/feed", "machine learning"]',         '["rss"]',              3, 2, 1, '0 */6 * * *'),
(4, 3, '产品设计动态',   '["product design", "UX trends"]',                                '["api"]',              2, 3, 1, NULL),
(5, 4, '安全资讯采集',   '["cybersecurity", "CVE", "vulnerability"]',                       '["rss", "web", "api"]', 2, 1, 1, '0 */1 * * *');

-- 内容（含语义去重标记和关联内容）
INSERT INTO content (id, subscription_id, source_platform, source_url, title, summary, content_body, author, published_at, fetched_at, content_hash, vector_id, `status`, is_duplicate, duplicate_of, related_contents) VALUES
('c7aa21d0-2205-4fce-b658-70f682e00001', 1, 'rss', 'https://example.com/ai-ml-2026',
 'AI与机器学习在自然语言处理中的最新进展',
 '<p>本文综述了2026年自然语言处理领域的最新突破，涵盖大语言模型微调、检索增强生成(RAG)、多模态融合等关键技术。</p>',
 '<article><h2>引言</h2><p>随着GPT-5、Claude 4等新一代大语言模型的发布，自然语言处理技术进入了新的发展阶段。本文将从预训练架构创新、高效微调策略、检索增强生成范式三个维度，系统梳理当前技术前沿。</p><h2>预训练架构创新</h2><p>MoE（混合专家）架构已成为主流选择，相比传统Dense架构在相同算力下可提升30%以上的模型容量。</p><h2>高效微调策略</h2><p>LoRA及其变体在保持微调效果的同时，将可训练参数量降低了99%以上。</p></article>',
 '张明', '2026-06-01 08:30:00', '2026-06-01 09:00:00', 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2', 'vec_001', 1, 0, NULL,
 '["0c8a071e-1d99-499b-86e6-eaddce3ef860", "2e119685-27ea-4ddf-a794-89450583d69b"]'),

('0af4bdb8-36c2-41b8-bf3c-5a6b7c8d9e0f', 1, 'web', 'https://example.com/ai-summary',
 'AI与机器学习在自然语言处理中的最新进展（摘要版）',
 '<p>2026年NLP领域最新突破综述：涵盖大语言模型微调、RAG、多模态融合等关键技术。</p>',
 '<p>本文简要介绍了NLP领域的最新进展，内容与另一篇文章高度重复。</p>',
 '匿名', '2026-06-01 10:00:00', '2026-06-01 10:05:00', 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3', 'vec_002', 1, 1,
 'c7aa21d0-2205-4fce-b658-70f682e00001', NULL),

('0c8a071e-1d99-499b-86e6-eaddce3ef860', 1, 'api', 'https://example.com/react19',
 'React 19 新特性全面解析与Server Components实践',
 '<p>React 19正式版发布，带来Server Components、Actions、Document Metadata等重大更新。</p>',
 '<article><h2>Server Components</h2><p>React Server Components允许组件在服务端渲染，显著减小客户端Bundle体积。</p><h2>Actions</h2><p>新引入的Actions机制简化了表单处理和数据变更流程。</p></article>',
 '李华', '2026-06-02 14:00:00', '2026-06-02 14:30:00', 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4', 'vec_003', 1, 0, NULL,
 '["c7aa21d0-2205-4fce-b658-70f682e00001"]'),

('2e119685-27ea-4ddf-a794-89450583d69b', 2, 'rss', 'https://example.com/rust-embedded',
 'Rust在嵌入式系统中的应用与实践',
 '<p>探讨Rust语言在嵌入式开发中的内存安全优势，以及no_std环境下的开发技巧。</p>',
 '<article><p>Rust凭借零成本抽象和所有权系统，在嵌入式领域迅速崛起。</p></article>',
 '王磊', '2026-06-03 11:00:00', '2026-06-03 11:20:00', 'd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5', 'vec_004', 1, 0, NULL,
 '["c7aa21d0-2205-4fce-b658-70f682e00001"]'),

('33502fbb-3ccb-4c05-9e7c-8d9e0f1a2b3c', 1, 'rss', 'https://example.com/transformers',
 'Do transformers need three projections? Systematic study of attention mechanisms',
 '<p>A systematic empirical study questioning whether Q, K, V projections are all necessary in transformer attention.</p>',
 '<p>Researchers conduct ablation studies across model scales, finding the Value projection contributes most to performance.</p>',
 'A. Krishnan', '2026-06-03 09:00:00', '2026-06-03 09:15:00', 'e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6', 'vec_005', 1, 0, NULL, NULL),

('3cb332f1-1f3e-42c9-b8d3-9e0f1a2b3c4d', 3, 'api', 'https://example.com/metaglasses',
 'Meta''s ships facial recognition on smart glasses',
 '<p>Meta begins shipping Ray-Ban smart glasses with on-device facial recognition, raising privacy concerns.</p>',
 '<p>The feature uses Qualcomm''s on-device AI engine to run face detection and recognition locally.</p>',
 'Sarah Chen', '2026-06-04 07:00:00', '2026-06-04 07:30:00', 'f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7', 'vec_006', 1, 0, NULL, NULL),

('62f66dc7-b9a0-44d1-a3c5-0f1a2b3c4d5e', 2, 'web', 'https://example.com/gaussian-splatting',
 'Gaussian Point Splatting: Real-time 3D scene rendering breakthrough',
 '<p>3D Gaussian Splatting achieves real-time photorealistic rendering, challenging NeRF-based approaches.</p>',
 '<article><p>The technique represents scenes as 3D Gaussians, achieving 30+ FPS rendering at 1080p.</p></article>',
 'Thomas Müller', '2026-06-05 16:00:00', '2026-06-05 16:45:00', 'a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8', 'vec_007', 1, 0, NULL, NULL),

('791d9dfc-a7fe-4e8b-b4d5-1a2b3c4d5e6f', 4, 'api', 'https://example.com/spacex-ipo',
 'SpaceX, Other Mega IPOs Denied Fast Index Inclusion by Nasdaq',
 '<p>Nasdaq rejects accelerated index inclusion for mega-IPOs exceeding $100B market cap.</p>',
 '<p>The decision affects how quickly mega-cap IPOs enter major indices.</p>',
 'Reuters', '2026-06-06 12:00:00', '2026-06-06 12:10:00', 'b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9', 'vec_008', 1, 0, NULL, NULL),

('7efd5df0-4b71-4a92-b5e6-2b3c4d5e6f7a', 5, 'rss', 'https://example.com/kvarn',
 'KVarN: Native vLLM backend for KV-cache aware quantization',
 '<p>KVarN introduces KV-cache aware quantization achieving 4-bit precision without accuracy loss.</p>',
 '<article><p>The method reduces memory footprint by 75% while maintaining perplexity within 0.1 of FP16 baseline.</p></article>',
 'J. Park', '2026-06-07 08:00:00', '2026-06-07 08:20:00', 'c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0', 'vec_009', 1, 0, NULL, NULL);

-- 审批工单
INSERT INTO approval_ticket (id, task_id, user_id, action_type, risk_level, context, `status`, approved_by, approved_at, comment) VALUES
(1, 'task_001', 2, 'content_publish', 2, '{"content_count": 5}', 0, NULL, NULL, NULL),
(2, 'task_002', 3, 'content_publish', 3, '{"content_count": 12, "contains_cve": true}', 0, NULL, NULL, NULL),
(3, 'task_003', 2, 'batch_delete', 1, '{"content_ids": ["abc", "def"]}', 1, 1, '2026-06-03 09:00:00', '已确认无风险，通过'),
(4, 'task_004', 4, 'content_publish', 2, '{"content_count": 3}', 2, 1, '2026-06-04 14:00:00', '内容来源不明确，拒绝'),
(5, 'task_005', 2, 'subscription_edit', 1, '{"subscription_id": 5}', 1, 1, '2026-06-05 10:00:00', '已审核通过');

-- 审计日志
INSERT INTO audit_log (id, user_id, `action`, target_type, target_id, action_time, ip_address) VALUES
(1, 1, 'LOGIN',          'user',     '1',  '2026-06-01 08:00:00', '192.168.1.100'),
(2, 2, 'CREATE_CONTENT', 'content',  'c7', '2026-06-01 09:00:00', '192.168.1.101'),
(3, 1, 'APPROVE_TICKET', 'approval', '3',  '2026-06-03 09:00:00', '192.168.1.100'),
(4, 2, 'TRIGGER_TASK',   'subscription', '1', '2026-06-01 09:05:00', '192.168.1.101'),
(5, 3, 'LOGIN',          'user',     '3',  '2026-06-02 14:00:00', '192.168.1.102'),
(6, 4, 'REJECT_TICKET',  'approval', '4',  '2026-06-04 14:00:00', '192.168.1.100');

-- 通知
INSERT INTO notification (id, user_id, `type`, title, content, is_read, related_id, created_at) VALUES
(1, 1, 'task',     '采集任务完成',       '订阅"AI技术前沿"采集到 3 条新内容',             1, 'task_001', '2026-06-01 09:30:00'),
(2, 1, 'system',   '系统维护通知',       '系统将于明晚22:00-24:00进行例行维护',            1, NULL,       '2026-06-02 08:00:00'),
(3, 2, 'task',     '采集任务完成',       '订阅"数据科学资讯"采集到 5 条新内容',             0, 'task_003', '2026-06-02 15:10:00'),
(4, 2, 'approval', '审批工单待处理',     '您有一条内容发布审批工单待处理',                  0, '1',        '2026-06-01 10:31:00'),
(5, 3, 'task',     '采集任务完成',       '订阅"产品设计动态"采集到 2 条新内容',             1, 'task_004', '2026-06-03 11:00:00'),
(6, 3, 'approval', '审批工单已处理',     '您的审批工单已通过',                             1, '3',        '2026-06-03 09:01:00'),
(7, 4, 'task',     '采集任务完成',       '订阅"安全资讯采集"采集到 8 条新内容',             0, 'task_005', '2026-06-05 10:00:00'),
(8, 4, 'approval', '审批工单已处理',     '您的审批工单已被拒绝',                           0, '4',        '2026-06-04 14:01:00'),
(9, 5, 'task',     '采集任务完成',       '首次采集完成，共获取 1 条内容',                  0, 'task_006', '2026-06-07 08:25:00'),
(10, 1, 'system',  '新功能上线',         'Agent监控页面已上线，可实时查看状态机执行状态',   0, NULL,       '2026-06-08 10:00:00');
