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


def init_db():
    os.makedirs("storage", exist_ok=True)
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_conn()
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()