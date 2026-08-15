#!/usr/bin/env python3
"""
初始化 legal.db
运行：python init_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "legal.db"
SCHEMA = Path(__file__).parent / "legal_schema.sql"


def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化：{DB_PATH}")


if __name__ == "__main__":
    init()
