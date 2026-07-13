import time
import threading

LOCK_TTL = 60

# In-memory lock state: { user_id: timestamp_when_locked }
_locks = {}
_lock_guard = threading.Lock()


def acquire(user_id):
    """
    Attempt to acquire the lock for a user.
    Returns True if acquired, False if already locked (and not expired).
    This check-and-set happens atomically under _lock_guard, so no race
    is possible between checking and setting the lock.
    """
    now = int(time.time())

    with _lock_guard:
        locked_at = _locks.get(user_id)

        if locked_at is not None and (now - locked_at) < LOCK_TTL:
            return False

        _locks[user_id] = now
        return True


def release(user_id):
    """Release the lock for a user, if any."""
    with _lock_guard:
        _locks.pop(user_id, None)


def is_locked(user_id):
    """Check if a user is currently locked (without acquiring)."""
    now = int(time.time())

    with _lock_guard:
        locked_at = _locks.get(user_id)
        if locked_at is not None and (now - locked_at) < LOCK_TTL:
            return True
        return False