import sqlite3
import os

DB_PATH = os.path.join("storage", "cache.db")


def get_conn():
    os.makedirs("storage", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        lastrowid = cur.lastrowid
        return lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def fetchall(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        raise e
    finally:
        conn.close()


def fetchone(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return row
    except Exception as e:
        raise e
    finally:
        conn.close()


def _add_column_if_missing(conn, table, column, coltype):
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    os.makedirs("storage", exist_ok=True)
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_conn()
    try:
        conn.executescript(sql)

        # One-time migration: adds the "part" column (for multi-part
        # episodes, e.g. "S02E01 Part 1" / "Part 2") to databases created
        # before this feature existed. Safe to run every startup — it's
        # a no-op once the column already exists.
        _add_column_if_missing(conn, "staging", "part", "INTEGER")
        _add_column_if_missing(conn, "episode_files", "part", "INTEGER")

        conn.commit()
    finally:
        conn.close()
