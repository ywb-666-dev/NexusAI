-- NexusAI baseline schema. Existing data is never deleted.

CREATE DATABASE IF NOT EXISTS nexusai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE nexusai;

CREATE TABLE IF NOT EXISTS agent_task (
	id VARCHAR(64) NOT NULL,
	subscription_id BIGINT NOT NULL,
	user_id BIGINT NOT NULL,
	status VARCHAR(80) NOT NULL,
	active_key VARCHAR(64),
	state JSON NOT NULL,
	nodes JSON NOT NULL,
	error TEXT,
	created_at DATETIME NOT NULL DEFAULT now(),
	updated_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (active_key)
);

CREATE INDEX idx_task_user_created ON agent_task (user_id, created_at);

CREATE TABLE IF NOT EXISTS approval_ticket (
	id BIGINT NOT NULL AUTO_INCREMENT,
	task_id VARCHAR(64) NOT NULL,
	user_id BIGINT NOT NULL,
	action_type VARCHAR(50),
	risk_level INTEGER,
	context JSON,
	status INTEGER NOT NULL,
	approved_by BIGINT,
	approved_at DATETIME,
	comment VARCHAR(500),
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS audit_log (
	id BIGINT NOT NULL AUTO_INCREMENT,
	user_id BIGINT,
	action VARCHAR(50) NOT NULL,
	target_type VARCHAR(50),
	target_id VARCHAR(64),
	action_time DATETIME NOT NULL DEFAULT now(),
	ip_address VARCHAR(64),
	request_id VARCHAR(64),
	PRIMARY KEY (id)
);

CREATE INDEX idx_audit_time ON audit_log (action_time);

CREATE TABLE IF NOT EXISTS content (
	id CHAR(36) NOT NULL,
	subscription_id BIGINT NOT NULL,
	task_id VARCHAR(64),
	source_platform VARCHAR(32) NOT NULL,
	source_url VARCHAR(1000) NOT NULL,
	title VARCHAR(500),
	summary VARCHAR(2000),
	translated_summary TEXT,
	quality JSON,
	relevance JSON,
	content_body LONGTEXT,
	author VARCHAR(100),
	published_at DATETIME,
	fetched_at DATETIME NOT NULL DEFAULT now(),
	content_hash CHAR(64) NOT NULL,
	vector_id VARCHAR(64),
	status INTEGER NOT NULL,
	is_duplicate INTEGER NOT NULL,
	duplicate_of CHAR(36),
	related_contents JSON,
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (content_hash)
);

CREATE INDEX idx_content_platform_duplicate ON content (source_platform, is_duplicate);

CREATE INDEX idx_content_hash ON content (content_hash);

CREATE INDEX idx_content_subscription ON content (subscription_id);

CREATE TABLE IF NOT EXISTS notification (
	id BIGINT NOT NULL AUTO_INCREMENT,
	user_id BIGINT NOT NULL,
	type VARCHAR(50) NOT NULL,
	title VARCHAR(200) NOT NULL,
	content TEXT,
	is_read INTEGER NOT NULL,
	related_id VARCHAR(64),
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE INDEX idx_notification_user_read ON notification (user_id, is_read);

CREATE TABLE IF NOT EXISTS push_channel (
	id BIGINT NOT NULL AUTO_INCREMENT,
	user_id BIGINT NOT NULL,
	name VARCHAR(100) NOT NULL,
	provider VARCHAR(20) NOT NULL,
	webhook TEXT NOT NULL,
	secret TEXT,
	enabled INTEGER NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS push_delivery (
	id BIGINT NOT NULL AUTO_INCREMENT,
	user_id BIGINT NOT NULL,
	task_id VARCHAR(64) NOT NULL,
	channel_id BIGINT NOT NULL,
	status VARCHAR(20) NOT NULL,
	attempts INTEGER NOT NULL,
	error VARCHAR(500),
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_delivery_task_channel UNIQUE (task_id, channel_id)
);

CREATE TABLE IF NOT EXISTS source_health (
	source_id VARCHAR(64) NOT NULL,
	status VARCHAR(24) NOT NULL,
	checked_at DATETIME,
	last_success_at DATETIME,
	latency_ms INTEGER,
	entry_count INTEGER NOT NULL,
	error VARCHAR(500),
	samples JSON NOT NULL,
	total_checks INTEGER NOT NULL,
	successful_checks INTEGER NOT NULL,
	consecutive_failures INTEGER NOT NULL,
	error_kind VARCHAR(40),
	next_check_at DATETIME,
	latest_item_at DATETIME,
	quality_score INTEGER,
	history JSON,
	PRIMARY KEY (source_id)
);

CREATE TABLE IF NOT EXISTS subscription (
	id BIGINT NOT NULL AUTO_INCREMENT,
	user_id BIGINT NOT NULL,
	name VARCHAR(100) NOT NULL,
	keywords JSON,
	source_platforms JSON,
	rss_feeds JSON,
	match_mode INTEGER NOT NULL,
	trigger_conditions JSON,
	priority INTEGER NOT NULL,
	status INTEGER NOT NULL,
	cron_expression VARCHAR(100),
	last_run_at DATETIME,
	created_at DATETIME NOT NULL DEFAULT now(),
	updated_at DATETIME,
	PRIMARY KEY (id)
);

CREATE INDEX idx_subscription_user_status ON subscription (user_id, status);

CREATE TABLE IF NOT EXISTS user (
	id BIGINT NOT NULL AUTO_INCREMENT,
	username VARCHAR(50) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	email VARCHAR(100),
	`role` VARCHAR(20) NOT NULL,
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS briefing (
	id VARCHAR(36) NOT NULL,
	user_id BIGINT NOT NULL,
	status VARCHAR(20) NOT NULL,
	active_key VARCHAR(64),
	schedule_key VARCHAR(80),
	hours INTEGER NOT NULL,
	period_start DATETIME NOT NULL,
	period_end DATETIME NOT NULL,
	report JSON,
	error TEXT,
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (active_key),
	UNIQUE (schedule_key)
);

CREATE INDEX idx_briefing_user_created ON briefing (user_id, created_at);

CREATE TABLE IF NOT EXISTS briefing_preference (
	user_id BIGINT NOT NULL,
	enabled INTEGER NOT NULL,
	push_enabled INTEGER NOT NULL,
	enabled_at DATETIME,
	PRIMARY KEY (user_id)
);
