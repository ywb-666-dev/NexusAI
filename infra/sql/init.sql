-- ============================================
-- NexusAI 数据库初始化脚本
-- 执行方式：sqlcmd -S localhost -U sa -P '<密码>' -i init.sql
-- ============================================

CREATE DATABASE NexusAI;
GO

USE NexusAI;
GO

-- 创建 Schema
CREATE SCHEMA app;
CREATE SCHEMA sec;
GO

-- ============================================
-- 1. 用户表 (app.user)
-- ============================================
CREATE TABLE app.[user] (
                            id BIGINT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    email NVARCHAR(100),
    [role] NVARCHAR(20) DEFAULT 'user',
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET()
    );

-- ============================================
-- 2. 订阅规则表 (app.subscription)
-- ============================================
CREATE TABLE app.subscription (
                                  id BIGINT IDENTITY(1,1) PRIMARY KEY,
                                  user_id BIGINT NOT NULL,
                                  name NVARCHAR(100) NOT NULL,
                                  keywords NVARCHAR(MAX),              -- JSON 数组
                                  source_platforms NVARCHAR(500),      -- JSON 数组
                                  match_mode TINYINT DEFAULT 1,        -- 1=精确 2=模糊 3=语义
                                  trigger_conditions NVARCHAR(MAX),    -- JSON DSL
                                  priority TINYINT DEFAULT 2,          -- 1=高 2=中 3=低
    [status] TINYINT DEFAULT 1,          -- 0=暂停 1=启用
                                  cron_expression NVARCHAR(100),
                                  last_run_at DATETIMEOFFSET,
                                  created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),
                                  updated_at DATETIMEOFFSET
);

CREATE INDEX IX_subscription_user_status ON app.subscription(user_id, [status]);

-- ============================================
-- 3. 内容表 (app.content)
-- ============================================
CREATE TABLE app.content (
                             id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                             subscription_id BIGINT NOT NULL,
                             source_platform NVARCHAR(32) NOT NULL,
                             source_url NVARCHAR(1000) NOT NULL,
                             title NVARCHAR(500),
                             summary NVARCHAR(2000),
                             content_body NVARCHAR(MAX),
                             author NVARCHAR(100),
                             published_at DATETIMEOFFSET,
                             fetched_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),
                             content_hash CHAR(64) NOT NULL UNIQUE,
                             vector_id VARCHAR(64),
    [status] TINYINT DEFAULT 1,          -- 0=删除 1=有效
                             is_duplicate TINYINT DEFAULT 0,      -- 0=正常 1=重复
                             duplicate_of UNIQUEIDENTIFIER NULL,
                             related_contents NVARCHAR(MAX),      -- JSON 数组
                             created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET()
);

CREATE INDEX IX_content_subscription ON app.content(subscription_id);
CREATE INDEX IX_content_hash ON app.content(content_hash);
CREATE INDEX IX_content_platform_duplicate ON app.content(source_platform) WHERE is_duplicate = 0;

-- ============================================
-- 4. 审批工单表 (app.approval_ticket) [占位，Phase 3 使用]
-- ============================================
CREATE TABLE app.approval_ticket (
                                     id BIGINT IDENTITY(1,1) PRIMARY KEY,
                                     task_id VARCHAR(64) NOT NULL,
                                     user_id BIGINT NOT NULL,
                                     action_type NVARCHAR(50),
                                     risk_level TINYINT CHECK (risk_level IN (1,2,3)), -- 1=低 2=中 3=高
                                     context NVARCHAR(MAX),
    [status] TINYINT DEFAULT 0,          -- 0=待审批 1=通过 2=拒绝
                                     approved_by BIGINT NULL,
                                     approved_at DATETIMEOFFSET NULL,
                                     comment NVARCHAR(500),
                                     created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET()
);

-- ============================================
-- 5. 审计日志表 (sec.audit_log) [占位，Phase 4 使用]
-- ============================================
CREATE TABLE sec.audit_log (
                               id BIGINT IDENTITY(1,1) PRIMARY KEY,
                               user_id BIGINT,
    [action] NVARCHAR(50) NOT NULL,
    target_type NVARCHAR(50),
    target_id VARCHAR(64),
    action_time DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),
    ip_address NVARCHAR(64),
    request_id VARCHAR(64)
    );

CREATE INDEX IX_audit_time ON sec.audit_log(action_time DESC);
GO