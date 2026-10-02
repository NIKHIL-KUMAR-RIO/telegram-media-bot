import sqlite3
import os

DB_PATH = os.path.join("storage", "cache.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()


def fetchall(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def fetchone(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


def is_approved(user_id):
    row = fetchall("SELECT * FROM approved_users WHERE user_id=?", (user_id,))
    return len(row) > 0


def init_db():
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_conn()
    conn.executescript(sql)
    conn.commit()

    # Lightweight migration: add a "name" column to approved_users
    # if it doesn't already exist (safe on both fresh and existing DBs).
    try:
        conn.execute("ALTER TABLE approved_users ADD COLUMN name TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists, nothing to do

    # Lightweight migration: add a "category" column to movies/staging
    # for the Movies vs LEGO Films split. SQLite backfills existing
    # rows with the DEFAULT value automatically.
    try:
        conn.execute("ALTER TABLE movies ADD COLUMN category TEXT DEFAULT 'movie'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE staging ADD COLUMN category TEXT DEFAULT 'movie'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()

def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id