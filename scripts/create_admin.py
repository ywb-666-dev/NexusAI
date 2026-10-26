"""Interactive administrator initialization. No default password or credential file."""

import argparse
import getpass
import re
import sys
from pathlib import Path
import bcrypt
import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nexus-python"))
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", args.username):
        raise ValueError("Use a username of 3-20 letters, digits or underscores.")
    password = getpass.getpass("Administrator password (at least 12 characters): ")
    if len(password) < 12 or len(password.encode()) > 72:
        raise ValueError("Use 12+ characters and no more than 72 UTF-8 bytes.")
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match.")
    cfg = settings.db
    with pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.username,
        password=cfg.password,
        database=cfg.database,
        charset="utf8mb4",
        autocommit=True,
    ) as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM user WHERE username=%s", (args.username,))
            if cursor.fetchone():
                raise ValueError("Username already exists. No account was changed.")
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "INSERT INTO user(username,password_hash,role) VALUES(%s,%s,%s)",
                (args.username, hashed, "admin"),
            )
    print("Administrator created. The password was not logged or saved to disk.")


if __name__ == "__main__":
    main()
