"""Non-destructive initialization and additive migration. Run from any directory."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nexus-python"))
import pymysql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from app.core.config import settings
from app.models import Base
from app.models.delivery import PushChannel, PushDelivery
from app.models.audit import AuditLog
from app.models.source import SourceHealth


def main():
    config = settings.db
    if not re.fullmatch(r"[A-Za-z0-9_]+", config.database):
        raise ValueError("Invalid database name")
    with pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.username,
        password=config.password,
        autocommit=True,
        charset="utf8mb4",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    engine = create_engine(
        URL.create(
            "mysql+pymysql",
            username=config.username,
            password=config.password,
            host=config.host,
            port=config.port,
            database=config.database,
        ),
        pool_pre_ping=True,
    )
    Base.metadata.create_all(engine)
    migrations = {
        "subscription": {"rss_feeds": "JSON"},
        "content": {
            "translated_summary": "TEXT",
            "task_id": "VARCHAR(64)",
            "quality": "JSON",
            "relevance": "JSON",
        },
        "source_health": {
            "total_checks": "INTEGER NOT NULL DEFAULT 0",
            "successful_checks": "INTEGER NOT NULL DEFAULT 0",
            "consecutive_failures": "INTEGER NOT NULL DEFAULT 0",
            "error_kind": "VARCHAR(40)",
            "next_check_at": "DATETIME",
            "latest_item_at": "DATETIME",
            "quality_score": "INTEGER",
            "history": "JSON",
        },
    }
    with engine.begin() as conn:
        for table, fields in migrations.items():
            existing = {c["name"] for c in inspect(conn).get_columns(table)}
            for name, ddl in fields.items():
                if name not in existing:
                    conn.execute(
                        text(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {ddl}")
                    )
        body_type = next(
            c["type"]
            for c in inspect(conn).get_columns("content")
            if c["name"] == "content_body"
        )
        if str(body_type).upper() != "LONGTEXT":
            conn.execute(
                text("ALTER TABLE content MODIFY COLUMN content_body LONGTEXT NULL")
            )
    print(
        "Database initialized; existing rows preserved. Tables:",
        ", ".join(inspect(engine).get_table_names()),
    )
    engine.dispose()


if __name__ == "__main__":
    main()
