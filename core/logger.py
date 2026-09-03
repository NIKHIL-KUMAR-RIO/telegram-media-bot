import time
from db import execute, fetchall


def log_action(user_id, action, detail=""):
    """
    Records a single user action (command used, file downloaded, etc.)
    into the activity_log table. Safe to call frequently — failures here
    are swallowed so logging never breaks the bot's actual functionality.
    """
    try:
        execute(
            "INSERT INTO activity_log (user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, detail, int(time.time()))
        )
    except Exception as e:
        print(f"[logger] Failed to log action: {e}")


def get_recent_activity(limit=20):
    """Returns the most recent N activity_log rows, newest first."""
    return fetchall(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )


def get_user_activity(user_id, limit=20):
    """Returns the most recent N activity_log rows for a specific user."""
    return fetchall(
        "SELECT * FROM activity_log WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
