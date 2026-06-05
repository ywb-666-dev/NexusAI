"""
初始化 NexusAI MySQL 数据库
用法: python scripts/init_db.py
"""
import sys
import os

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nexus-python'))

try:
    import pymysql
except ImportError:
    print("正在安装 pymysql...")
    os.system(f"{sys.executable} -m pip install pymysql -q")
    import pymysql

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "712693"
DB_NAME = "nexusai"

SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'infra', 'sql', 'init.sql')

def init_database():
    # 1. 创建数据库
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 '{DB_NAME}' 创建成功（或已存在）")
        conn.commit()
    finally:
        conn.close()

    # 2. 执行 init.sql
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cur:
            with open(SQL_FILE, 'r', encoding='utf-8') as f:
                sql = f.read()
            # 按分号分割语句（简单处理）
            for statement in sql.split(';'):
                stmt = statement.strip()
                if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
                    # 移除注释行
                    clean_lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
                    clean_stmt = '\n'.join(clean_lines).strip()
                    if clean_stmt:
                        cur.execute(clean_stmt)
                        print(f"执行: {clean_stmt[:60]}...")
        conn.commit()
        print("init.sql 执行完毕")
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
    print("数据库初始化完成！")
