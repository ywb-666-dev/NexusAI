-- ============================================
-- NexusAI MySQL 数据库初始化脚本
-- 执行方式：mysql -u root -p < init.sql
-- ============================================

CREATE DATABASE IF NOT EXISTS nexusai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE nexusai;

-- ============================================
-- 1. 用户表 (user)
-- ============================================
CREATE TABLE IF NOT EXISTS `user` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    `role` VARCHAR(20) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 订阅规则表 (subscription)
-- ============================================
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

-- ============================================
-- 3. 内容表 (content)
-- ============================================
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

-- ============================================
-- 4. 审批工单表 (approval_ticket)
-- ============================================
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

-- ============================================
-- 5. 审计日志表 (audit_log)
-- ============================================
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

-- ============================================
-- 6. 通知表 (notification)
-- ============================================
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
