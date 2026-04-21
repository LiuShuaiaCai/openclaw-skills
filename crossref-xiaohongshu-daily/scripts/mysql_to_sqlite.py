"""
MySQL → SQLite 数据迁移脚本
将 MySQL 中的 journals 和 countries 表导出为 SQLite 数据库
"""

import pymysql
import sqlite3
import os
import sys
from decimal import Decimal

# ──────────────────────────────────────────────
# MySQL 配置
# ──────────────────────────────────────────────
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "express",
    "charset": "utf8mb4"
}

# ──────────────────────────────────────────────
# SQLite 输出路径
# ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DIR = os.path.join(SCRIPT_DIR, "data")
SQLITE_PATH = os.path.join(SQLITE_DIR, "crossref_data.db")

def convert_value(value):
    """转换 Decimal 类型为 float，None 保持 None"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

def export_table(mysql_conn, table_name, sqlite_conn):
    """导出单个表 - 自动检测列结构"""
    print(f"\n[EXPORT] 正在导出表: {table_name}")

    # 获取 MySQL 列结构
    cursor = mysql_conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if not columns:
        print(f"[WARN] 表 {table_name} 无列信息")
        return 0

    # 创建 SQLite 表
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    create_sql += ", ".join([f'"{col}" TEXT' for col in columns])
    create_sql += ")"
    sqlite_conn.execute(create_sql)

    # 获取 MySQL 数据
    cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        print(f"[WARN] 表 {table_name} 无数据")
        return 0

    # 批量插入
    placeholders = ','.join(['?' for _ in columns])
    columns_str = ','.join([f'"{col}"' for col in columns])
    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"

    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        for row in batch:
            values = [convert_value(row.get(col)) for col in columns]
            sqlite_conn.execute(insert_sql, values)
        sqlite_conn.commit()
        print(f"  已插入 {min(i+batch_size, len(rows))}/{len(rows)} 条")

    print(f"[OK] 表 {table_name} 导出完成: {len(rows)} 条")
    return len(rows)

def main():
    print("="*60)
    print("  MySQL → SQLite 数据迁移")
    print("="*60)

    # 确保输出目录存在
    os.makedirs(SQLITE_DIR, exist_ok=True)

    # 删除已存在的 SQLite 数据库
    if os.path.exists(SQLITE_PATH):
        print(f"\n[INFO] 删除旧的 SQLite 数据库: {SQLITE_PATH}")
        os.remove(SQLITE_PATH)

    # 连接 MySQL
    print("\n[CONNECT] 连接 MySQL...")
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        print("[OK] MySQL 连接成功")
    except Exception as e:
        print(f"[ERROR] MySQL 连接失败: {e}")
        sys.exit(1)

    # 创建 SQLite 数据库
    print(f"\n[CREATE] 创建 SQLite 数据库: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    try:
        # 导出 journals 表
        journals_count = export_table(mysql_conn, "journals", sqlite_conn)

        # 导出 countries 表
        countries_count = export_table(mysql_conn, "countries", sqlite_conn)

    finally:
        mysql_conn.close()
        sqlite_conn.close()

    print("\n" + "="*60)
    print("  迁移完成!")
    print(f"  journals: {journals_count} 条")
    print(f"  countries: {countries_count} 条")
    print(f"  SQLite 路径: {SQLITE_PATH}")
    print("="*60)

if __name__ == "__main__":
    main()
