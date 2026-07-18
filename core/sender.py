import asyncio
from db import fetchall
from core.locks import acquire, release


async def send_movie(bot, chat_id, movie_id):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        files = fetchall(
            "SELECT * FROM movie_files WHERE movie_id=?",
            (movie_id,)
        )

        if not files:
            await bot.send_message(chat_id, "❌ No files found for this movie.")
            return

        for f in files:
            await bot.send_document(chat_id, f["file_id"])
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"[sender] Error sending movie: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the file.")

    finally:
        release(chat_id)


async def send_episode(bot, chat_id, episode_id):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        files = fetchall(
            "SELECT * FROM episode_files WHERE episode_id=? ORDER BY part",
            (episode_id,)
        )

        if not files:
            await bot.send_message(chat_id, "❌ No files found for this episode.")
            return

        for f in files:
            await bot.send_document(chat_id, f["file_id"])
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"[sender] Error sending episode: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the file.")

    finally:
        release(chat_id)


async def send_season(bot, chat_id, season_id):
    if not acquire(chat_id):
        await bot.send_message(chat_id, "⏳ Please wait, another request is still being processed.")
        return

    try:
        eps = fetchall(
            "SELECT * FROM episodes WHERE season_id=? ORDER BY episode_number",
            (season_id,)
        )

        if not eps:
            await bot.send_message(chat_id, "❌ No episodes found for this season.")
            return

        for e in eps:
            files = fetchall(
                "SELECT * FROM episode_files WHERE episode_id=? ORDER BY part",
                (e["id"],)
            )

            for f in files:
                await bot.send_document(chat_id, f["file_id"])
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"[sender] Error sending season: {e}")
        await bot.send_message(chat_id, "❌ Something went wrong while sending the files.")

    finally:
        release(chat_id)
