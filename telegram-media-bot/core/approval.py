from db import fetchall, fetchone, execute


def run_approval():
    rows = fetchall("""
        SELECT * FROM staging
        WHERE status='pending'
        ORDER BY created_at ASC
    """)

    if not rows:
        return 0

    movie_cache = {}
    show_cache = {}
    processed_ids = []

    for r in rows:
        try:
            if r["media_type"] == "movie":
                _process_movie(r, movie_cache)
            else:
                _process_show(r, show_cache)

            execute(
                "UPDATE staging SET status='approved' WHERE id=?",
                (r["id"],)
            )
            processed_ids.append(r["id"])

        except Exception as e:
            print(f"[approval] Failed to process staging id={r['id']}: {e}")

    # clean up approved rows
    execute("DELETE FROM staging WHERE status='approved'")

    return len(processed_ids)


def _get_next_order_index(table):
    row = fetchone(f"SELECT MAX(order_index) as max_idx FROM {table}")
    return (row["max_idx"] or 0) + 1


def _get_or_create_movie(title, year, category):
    # Match on title AND year so movies that share a title
    # (e.g. remakes) but have different years are kept as
    # separate entries instead of being merged together.
    existing = fetchall(
        "SELECT id FROM movies WHERE title=? AND year=?",
        (title, year)
    )
    if existing:
        return existing[0]["id"]

    idx = _get_next_order_index("movies")
    movie_id = execute(
        "INSERT INTO movies (title, year, order_index, category) VALUES (?, ?, ?, ?)",
        (title, year, idx, category)
    )
    return movie_id


def _process_movie(r, movie_cache):
    # Cache key includes year so two movies with the same title
    # but different years are treated as distinct within a batch too.
    key = (r["title"], r["year"])

    if key not in movie_cache:
        category = r["category"] if "category" in r.keys() and r["category"] else "movie"
        movie_cache[key] = _get_or_create_movie(r["title"], r["year"], category)

    movie_id = movie_cache[key]

    existing_file = fetchall("""
        SELECT id FROM movie_files
        WHERE movie_id=? AND quality=?
    """, (movie_id, r["quality"]))

    if existing_file:
        execute("""
            UPDATE movie_files
            SET file_id=?
            WHERE id=?
        """, (r["file_id"], existing_file[0]["id"]))
    else:
        execute("""
            INSERT INTO movie_files (movie_id, quality, file_id)
            VALUES (?, ?, ?)
        """, (movie_id, r["quality"], r["file_id"]))


def _get_or_create_show(title):
    existing = fetchall(
        "SELECT id FROM shows WHERE title=?",
        (title,)
    )
    if existing:
        return existing[0]["id"]

    idx = _get_next_order_index("shows")
    show_id = execute(
        "INSERT INTO shows (title, order_index) VALUES (?, ?)",
        (title, idx)
    )
    return show_id


def _get_or_create_season(show_id, season_number):
    existing = fetchall("""
        SELECT id FROM seasons
        WHERE show_id=? AND season_number=?
    """, (show_id, season_number))

    if existing:
        return existing[0]["id"]

    season_id = execute("""
        INSERT INTO seasons (show_id, season_number)
        VALUES (?, ?)
    """, (show_id, season_number))
    return season_id


def _get_or_create_episode(season_id, episode_number):
    existing = fetchall("""
        SELECT id FROM episodes
        WHERE season_id=? AND episode_number=?
    """, (season_id, episode_number))

    if existing:
        return existing[0]["id"]

    episode_id = execute("""
        INSERT INTO episodes (season_id, episode_number)
        VALUES (?, ?)
    """, (season_id, episode_number))
    return episode_id


def _process_show(r, show_cache):
    show_key = r["title"]

    if show_key not in show_cache:
        show_cache[show_key] = _get_or_create_show(r["title"])

    show_id = show_cache[show_key]
    season_id = _get_or_create_season(show_id, r["season"])

    # Get episode numbers from staging
    ep_start = r["episode"]
    ep_end = r["episode_end"] if r["episode_end"] else None

    # Create episodes
    episodes_to_link = [ep_start]
    if ep_end and ep_end != ep_start:
        episodes_to_link.append(ep_end)

    for ep_num in episodes_to_link:
        episode_id = _get_or_create_episode(season_id, ep_num)
        part = r["part"] if "part" in r.keys() else None

        # Match on part too (using IS to correctly match NULL=NULL), so
        # multi-part episodes (e.g. "S02E01 Part 1" and "Part 2") are
        # stored as separate files instead of one overwriting the other.
        existing_ep = fetchall("""
            SELECT id FROM episode_files
            WHERE episode_id=? AND quality=? AND part IS ?
        """, (episode_id, r["quality"], part))

        if existing_ep:
            execute("""
                UPDATE episode_files
                SET file_id=?
                WHERE id=?
            """, (r["file_id"], existing_ep[0]["id"]))
        else:
            execute("""
                INSERT INTO episode_files (episode_id, quality, part, file_id)
                VALUES (?, ?, ?, ?)
            """, (episode_id, r["quality"], part, r["file_id"]))
