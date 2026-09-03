import asyncio
from db import fetchall, fetchone
from core.locks import acquire, release
from core.logger import log_action

DELETE_AFTER_SECONDS = 3 * 60 * 60  # 3 hours

WARNING_TEXT = (
    "⚠️ Please download your file(s) now.\n"
    "They will be automatically deleted from this chat in 3 hours."
)


async def _delete_message_job(context):
    """Runs once, 3 hours after a file was sent, and deletes it."""
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception:
        # Already deleted, chat cleared, or message too old to delete — ignore.
        pass


def _schedule_deletion(job_queue, chat_id, message_id):
    if job_queue is None:
        return
    job_queue.run_once(
        _delete_message_job,
        DELETE_AFTER_SECONDS,
        chat_id=chat_id,
        data=message_id,
    )


async def send_movie(bot, chat_id, movie_id, job_queue=None):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        movie = fetchone("SELECT * FROM movies WHERE id=?", (movie_id,))
        files = fetchall(
            "SELECT * FROM movie_files WHERE movie_id=?",
            (movie_id,)
        )

        if not files:
            await bot.send_message(chat_id, "❌ No files found for this movie.")
            return

        title = movie["title"] if movie else "Unknown movie"

        sent_any = False
        for f in files:
            msg = await bot.send_document(chat_id, f["file_id"])
            _schedule_deletion(job_queue, chat_id, msg.message_id)
            log_action(chat_id, "download_movie", f"{title} — {f['quality']}")
            sent_any = True
            await asyncio.sleep(0.5)

        if sent_any:
            await bot.send_message(chat_id, WARNING_TEXT)

    except Exception as e:
        print(f"[sender] Error sending movie: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the file.")

    finally:
        release(chat_id)


async def send_episode(bot, chat_id, episode_id, job_queue=None):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        ep_info = fetchone(
            """
            SELECT episodes.episode_number, seasons.season_number, shows.title
            FROM episodes
            JOIN seasons ON seasons.id = episodes.season_id
            JOIN shows ON shows.id = seasons.show_id
            WHERE episodes.id=?
            """,
            (episode_id,)
        )

        files = fetchall(
            "SELECT * FROM episode_files WHERE episode_id=? ORDER BY part",
            (episode_id,)
        )

        if not files:
            await bot.send_message(chat_id, "❌ No files found for this episode.")
            return

        if ep_info:
            label = f"{ep_info['title']} S{ep_info['season_number']:02d}E{ep_info['episode_number']:02d}"
        else:
            label = "Unknown episode"

        sent_any = False
        for f in files:
            msg = await bot.send_document(chat_id, f["file_id"])
            _schedule_deletion(job_queue, chat_id, msg.message_id)
            log_action(chat_id, "download_episode", f"{label} — {f['quality']}")
            sent_any = True
            await asyncio.sleep(0.5)

        if sent_any:
            await bot.send_message(chat_id, WARNING_TEXT)

    except Exception as e:
        print(f"[sender] Error sending episode: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the file.")

    finally:
        release(chat_id)


async def send_season(bot, chat_id, season_id, job_queue=None):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        season_row = fetchone(
            """
            SELECT seasons.season_number, shows.title
            FROM seasons
            JOIN shows ON shows.id = seasons.show_id
            WHERE seasons.id=?
            """,
            (season_id,)
        )

        eps = fetchall(
            "SELECT * FROM episodes WHERE season_id=? ORDER BY episode_number",
            (season_id,)
        )

        if not eps:
            await bot.send_message(chat_id, "❌ No episodes found for this season.")
            return

        sent_any = False
        for e in eps:
            files = fetchall(
                "SELECT * FROM episode_files WHERE episode_id=? ORDER BY part",
                (e["id"],)
            )

            for f in files:
                msg = await bot.send_document(chat_id, f["file_id"])
                _schedule_deletion(job_queue, chat_id, msg.message_id)
                await asyncio.sleep(0.5)
                sent_any = True

        if sent_any and season_row:
            label = f"{season_row['title']} — Season {season_row['season_number']}"
            await bot.send_message(
                chat_id,
                f"✅ {label} sent in full."
            )
            log_action(chat_id, "download_full_season", label)
        elif sent_any:
            await bot.send_message(chat_id, "✅ Full season sent.")
            log_action(chat_id, "download_full_season", f"season_id={season_id}")
        else:
            await bot.send_message(chat_id, "❌ No files found for this season.")

        if sent_any:
            await bot.send_message(chat_id, WARNING_TEXT)

    except Exception as e:
        print(f"[sender] Error sending season: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the files.")

    finally:
        release(chat_id)
