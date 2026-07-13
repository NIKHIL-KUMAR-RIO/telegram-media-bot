import time
from db import execute, fetchall


def add(parsed, file_id, file_name):
    """
    Save a detected file straight into the staging table (status='pending').
    No in-memory buffering — this survives a bot restart, since it's
    committed to the database the moment a file is detected.
    """
    if not parsed.get("valid"):
        return False

    execute("""
        INSERT INTO staging
        (file_id, file_name, media_type, title, year, season, episode, episode_end, quality, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        file_name,
        parsed["type"],
        parsed["title"],
        parsed.get("year"),
        parsed.get("season"),
        parsed.get("episode_start"),
        parsed.get("episode_end"),
        parsed.get("quality", "unknown"),
        int(time.time())
    ))

    return True


def get_pending():
    return fetchall("SELECT * FROM staging WHERE status='pending' ORDER BY created_at ASC")


def clear_processed():
    execute("DELETE FROM staging WHERE status='approved'")
