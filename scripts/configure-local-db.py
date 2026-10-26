"""Only called immediately after initializing the project's own new data directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nexus-python"))
import pymysql
from app.core.config import settings

with pymysql.connect(
    host="127.0.0.1", user="root", password="", autocommit=True
) as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            "ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (settings.db.password,)
        )
print("Local database credentials configured.")
