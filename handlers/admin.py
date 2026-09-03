import time
import os
import shutil
import html
from datetime import datetime
from config import ADMIN_ID, CHANNEL_ID
from core.staging import get_pending, add
from core.approval import run_approval
from core.parser import parse
from db import fetchall, fetchone, execute, is_approved
from core.logger import get_recent_activity
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def is_admin(update):
    return update.effective_user.id == ADMIN_ID


async def _get_display_name(context, user_id):
    """
    Looks up a user's name via Telegram. Works as long as the user has
    interacted with the bot before (which is true for both approval
    flows — they've either sent /start or triggered a request).
    Falls back to 'Unknown' if the lookup fails for any reason.
    """
    try:
        chat = await context.bot.get_chat(user_id)
        return chat.first_name or chat.username or "Unknown"
    except Exception:
        return "Unknown"


async def done(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    pending = get_pending()

    if not pending:
        await update.message.reply_text("ℹ️ No pending files to save.")
        return

    count = run_approval()

    if count == 0:
        await update.message.reply_text("❌ No files were approved. Check logs for errors.")
    else:
        await update.message.reply_text(f"✅ {count} file(s) saved to database successfully.")


async def approve(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    args = context.args

    if not args:
        await update.message.reply_text(
            "ℹ️ Usage: /approve <telegram_id>\n"
            "Example: /approve 123456789"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid Telegram ID. It must be a number.")
        return

    already = fetchall("SELECT * FROM approved_users WHERE user_id=?", (target_id,))
    if already:
        await update.message.reply_text(f"ℹ️ User `{target_id}` is already approved.", parse_mode="Markdown")
        return

    name = await _get_display_name(context, target_id)

    execute(
        "INSERT INTO approved_users (user_id, name, approved_at) VALUES (?, ?, ?)",
        (target_id, name, int(time.time()))
    )

    await update.message.reply_text(f"✅ User `{target_id}` ({name}) has been approved.", parse_mode="Markdown")

    try:
        await context.bot.send_message(
            target_id,
            "✅ You have been approved! Send /start to begin."
        )
    except Exception:
        await update.message.reply_text("⚠️ Could not notify the user. They may not have started the bot yet.")


async def revoke(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    args = context.args

    if not args:
        await update.message.reply_text(
            "ℹ️ Usage: /revoke <telegram_id>\n"
            "Example: /revoke 123456789"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid Telegram ID. It must be a number.")
        return

    existing = fetchall("SELECT * FROM approved_users WHERE user_id=?", (target_id,))
    if not existing:
        await update.message.reply_text(f"ℹ️ User `{target_id}` is not in the approved list.", parse_mode="Markdown")
        return

    execute("DELETE FROM approved_users WHERE user_id=?", (target_id,))
    await update.message.reply_text(f"✅ User `{target_id}` has been revoked.", parse_mode="Markdown")


async def list_users(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    rows = fetchall("SELECT * FROM approved_users")

    if not rows:
        await update.message.reply_text("ℹ️ No approved users yet.")
        return

    text = "👥 *Approved Users:*\n\n"
    for r in rows:
        name = r["name"] if "name" in r.keys() and r["name"] else "Unknown"
        text += f"• `{r['user_id']}` - {name}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_access_request(update, context):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("requestaccess_"):
        user_id = int(data.split("_", 1)[1])
        first_name = update.effective_user.first_name

        already = fetchall("SELECT * FROM approved_users WHERE user_id=?", (user_id,))
        if already:
            await q.message.edit_text("✅ You are already approved! Send /start to begin.")
            return

        lock_row = fetchone("SELECT status FROM user_locks WHERE user_id=?", (user_id,))
        if lock_row and lock_row["status"] == "pending":
            await q.message.edit_text(
                "⏳ Your request has already been sent.\n"
                "Please wait for the admin to approve it."
            )
            return

        execute(
            "INSERT INTO user_locks (user_id, status, updated_at) VALUES (?, 'pending', ?) "
            "ON CONFLICT(user_id) DO UPDATE SET status='pending', updated_at=excluded.updated_at",
            (user_id, int(time.time()))
        )

        kb = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"grantaccess_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rejectaccess_{user_id}")
            ]
        ]

        await context.bot.send_message(
            ADMIN_ID,
            f"👤 *New Access Request*\n\n"
            f"Name: {first_name}\n"
            f"ID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

        await q.message.edit_text(
            "✅ Your request has been sent to the admin.\n"
            "You will be notified once approved."
        )

    elif data.startswith("grantaccess_"):
        user_id = int(data.split("_", 1)[1])

        already = fetchall("SELECT * FROM approved_users WHERE user_id=?", (user_id,))
        if already:
            await q.message.edit_text(f"ℹ️ User `{user_id}` is already approved.", parse_mode="Markdown")
            return

        name = await _get_display_name(context, user_id)

        execute(
            "INSERT INTO approved_users (user_id, name, approved_at) VALUES (?, ?, ?)",
            (user_id, name, int(time.time()))
        )

        execute(
            "UPDATE user_locks SET status='free', updated_at=? WHERE user_id=?",
            (int(time.time()), user_id)
        )

        await q.message.edit_text(f"✅ User `{user_id}` ({name}) has been approved.", parse_mode="Markdown")

        try:
            await context.bot.send_message(
                user_id,
                "✅ Your access has been approved! Send /start to begin."
            )
        except Exception:
            pass

    elif data.startswith("rejectaccess_"):
        user_id = int(data.split("_", 1)[1])

        execute(
            "UPDATE user_locks SET status='free', updated_at=? WHERE user_id=?",
            (int(time.time()), user_id)
        )

        await q.message.edit_text(f"❌ User `{user_id}` has been rejected.", parse_mode="Markdown")

        try:
            await context.bot.send_message(
                user_id,
                "❌ Your access request has been rejected."
            )
        except Exception:
            pass


async def media_request(update, context):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    if user_id != ADMIN_ID and not is_approved(user_id):
        await update.message.reply_text("⛔ You don't have access to this bot.")
        return

    if not context.args:
        await update.message.reply_text(
            "ℹ️ Usage: /request <what you want>\n"
            "Example: /request Clone Wars Season 2"
        )
        return

    request_text = " ".join(context.args)

    kb = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approverequest_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejectrequest_{user_id}")
        ]
    ]

    await context.bot.send_message(
        ADMIN_ID,
        f"📩 *New Media Request*\n\n"
        f"From: {first_name}\n"
        f"ID: `{user_id}`\n\n"
        f"Request: *{request_text}*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ Your request has been sent!")


async def handle_media_request(update, context):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("approverequest_"):
        user_id = int(data.split("_", 1)[1])

        await q.message.edit_text(
            q.message.text + "\n\n✅ Approved",
            parse_mode="Markdown"
        )

        try:
            await context.bot.send_message(
                user_id,
                "✅ Your request has been approved! The owner will look into it and add it soon."
            )
        except Exception:
            pass

    elif data.startswith("rejectrequest_"):
        user_id = int(data.split("_", 1)[1])

        await q.message.edit_text(
            q.message.text + "\n\n❌ Rejected",
            parse_mode="Markdown"
        )

        try:
            await context.bot.send_message(
                user_id,
                "❌ Your request was not approved."
            )
        except Exception:
            pass


# -------------------------
# DELETE MEDIA
# -------------------------
async def delete_media(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "ℹ️ Usage: /delete <name>\n"
            "Example: /delete The Dark Knight\n"
            "Example: /delete Star Wars Young Jedi Adventures"
        )
        return

    name = " ".join(context.args)

    # Search movies
    movies = fetchall(
        "SELECT * FROM movies WHERE title LIKE ?", (f"%{name}%",)
    )

    # Search shows
    shows = fetchall(
        "SELECT * FROM shows WHERE title LIKE ?", (f"%{name}%",)
    )

    if not movies and not shows:
        await update.message.reply_text(f"❌ Nothing found matching: *{name}*", parse_mode="Markdown")
        return

    # Build response
    for movie in movies:
        kb = [
            [
                InlineKeyboardButton("🗑️ Confirm Delete", callback_data=f"delmovie_{movie['id']}"),
                InlineKeyboardButton("❌ Cancel", callback_data="delcancel")
            ]
        ]
        await update.message.reply_text(
            f"🎬 Found Movie: *{movie['title']}* ({movie['year'] or 'N/A'})\n\nConfirm delete?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    for show in shows:
        seasons = fetchall(
            "SELECT * FROM seasons WHERE show_id=? ORDER BY season_number", (show["id"],)
        )

        kb = [
            [InlineKeyboardButton("🗑️ Delete Entire Show", callback_data=f"delshow_{show['id']}")]
        ]

        for season in seasons:
            kb.append([
                InlineKeyboardButton(
                    f"🗑️ Delete Season {season['season_number']}",
                    callback_data=f"delseason_{season['id']}_{show['id']}"
                )
            ])

        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="delcancel")])

        await update.message.reply_text(
            f"📺 Found Show: *{show['title']}*\n\nWhat do you want to delete?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )


async def handle_delete(update, context):
    q = update.callback_query
    await q.answer()

    data = q.data

    # Cancel
    if data == "delcancel":
        await q.message.edit_text("❌ Deletion cancelled.")
        return

    # Delete movie
    elif data.startswith("delmovie_"):
        movie_id = int(data.split("_", 1)[1])

        movie = fetchall("SELECT * FROM movies WHERE id=?", (movie_id,))
        if not movie:
            await q.message.edit_text("❌ Movie not found.")
            return

        title = movie[0]["title"]
        execute("DELETE FROM movie_files WHERE movie_id=?", (movie_id,))
        execute("DELETE FROM movies WHERE id=?", (movie_id,))

        await q.message.edit_text(f"✅ *{title}* has been deleted.", parse_mode="Markdown")

    # Delete entire show
    elif data.startswith("delshow_"):
        show_id = int(data.split("_", 1)[1])

        show = fetchall("SELECT * FROM shows WHERE id=?", (show_id,))
        if not show:
            await q.message.edit_text("❌ Show not found.")
            return

        title = show[0]["title"]
        _delete_show(show_id)

        await q.message.edit_text(f"✅ *{title}* has been fully deleted.", parse_mode="Markdown")

    # Delete a season
    elif data.startswith("delseason_"):
        parts = data.split("_", 2)
        season_id = int(parts[1])
        show_id = int(parts[2])

        season = fetchall("SELECT * FROM seasons WHERE id=?", (season_id,))
        show = fetchall("SELECT * FROM shows WHERE id=?", (show_id,))

        if not season or not show:
            await q.message.edit_text("❌ Season not found.")
            return

        season_number = season[0]["season_number"]
        show_title = show[0]["title"]

        _delete_season(season_id)

        # If no seasons left, delete the show too
        remaining = fetchall("SELECT * FROM seasons WHERE show_id=?", (show_id,))
        if not remaining:
            execute("DELETE FROM shows WHERE id=?", (show_id,))
            await q.message.edit_text(
                f"✅ Season {season_number} deleted.\n"
                f"No seasons remaining — *{show_title}* has also been removed.",
                parse_mode="Markdown"
            )
        else:
            await q.message.edit_text(
                f"✅ Season {season_number} of *{show_title}* has been deleted.",
                parse_mode="Markdown"
            )


def _delete_show(show_id):
    seasons = fetchall("SELECT * FROM seasons WHERE show_id=?", (show_id,))
    for season in seasons:
        _delete_season(season["id"])
    execute("DELETE FROM seasons WHERE show_id=?", (show_id,))
    execute("DELETE FROM shows WHERE id=?", (show_id,))


def _delete_season(season_id):
    episodes = fetchall("SELECT * FROM episodes WHERE season_id=?", (season_id,))
    for ep in episodes:
        execute("DELETE FROM episode_files WHERE episode_id=?", (ep["id"],))
    execute("DELETE FROM episodes WHERE season_id=?", (season_id,))
    execute("DELETE FROM seasons WHERE id=?", (season_id,))


# -------------------------
# LIST MEDIA (for reference — IDs shown for convenience only,
# /rename itself works by name search, not by typing IDs)
# -------------------------
async def list_movies(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    rows = fetchall("SELECT * FROM movies ORDER BY order_index")
    if not rows:
        await update.message.reply_text("ℹ️ No movies saved yet.")
        return

    text = "🎬 *Movies:*\n\n"
    for m in rows:
        text += f"`[{m['id']}]` {m['title']} ({m['year'] or 'N/A'})\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def list_shows(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    rows = fetchall("SELECT * FROM shows ORDER BY order_index")
    if not rows:
        await update.message.reply_text("ℹ️ No shows saved yet.")
        return

    text = "📺 *Shows:*\n\n"
    for s in rows:
        text += f"`[{s['id']}]` {s['title']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def backup_db(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    db_path = os.path.join("storage", "cache.db")

    if not os.path.exists(db_path):
        await update.message.reply_text("❌ Database file not found.")
        return

    # Copy first so we send a stable snapshot even if the DB is
    # written to mid-upload (SQLite can be mid-write during polling).
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"cache_backup_{timestamp}.db"
    backup_path = os.path.join("storage", backup_name)

    try:
        shutil.copy2(db_path, backup_path)
        with open(backup_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=backup_name,
                caption=f"🗄️ Backup created {timestamp}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Backup failed: {e}")
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)


async def stats(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    movie_count = fetchone("SELECT COUNT(*) as c FROM movies")["c"]
    movie_file_count = fetchone("SELECT COUNT(*) as c FROM movie_files")["c"]

    show_count = fetchone("SELECT COUNT(*) as c FROM shows")["c"]
    season_count = fetchone("SELECT COUNT(*) as c FROM seasons")["c"]
    episode_count = fetchone("SELECT COUNT(*) as c FROM episodes")["c"]
    episode_file_count = fetchone("SELECT COUNT(*) as c FROM episode_files")["c"]

    user_count = fetchone("SELECT COUNT(*) as c FROM approved_users")["c"]

    db_path = os.path.join("storage", "cache.db")
    size_mb = (os.path.getsize(db_path) / (1024 * 1024)) if os.path.exists(db_path) else 0

    text = (
        "📊 *Archive Stats*\n\n"
        f"🎬 Movies: {movie_count} titles, {movie_file_count} files\n"
        f"📺 Shows: {show_count} shows, {season_count} seasons, "
        f"{episode_count} episodes, {episode_file_count} files\n"
        f"👥 Approved users: {user_count}\n"
        f"💾 Database size: {size_mb:.2f} MB"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# -------------------------
# RENAME MEDIA (title + quality)
# -------------------------
async def rename_media(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "ℹ️ Usage: /rename <name>\n"
            "Example: /rename The Dark Knight\n"
            "Example: /rename Star Wars Young Jedi Adventures"
        )
        return

    name = " ".join(context.args)

    movies = fetchall("SELECT * FROM movies WHERE title LIKE ?", (f"%{name}%",))
    shows = fetchall("SELECT * FROM shows WHERE title LIKE ?", (f"%{name}%",))

    if not movies and not shows:
        await update.message.reply_text(f"❌ Nothing found matching: *{name}*", parse_mode="Markdown")
        return

    for movie in movies:
        files = fetchall("SELECT * FROM movie_files WHERE movie_id=?", (movie["id"],))

        kb = [[InlineKeyboardButton("✏️ Rename Title", callback_data=f"renametitle_movie_{movie['id']}")]]
        for f in files:
            kb.append([InlineKeyboardButton(
                f"✏️ Quality: {f['quality']}",
                callback_data=f"renamequality_moviefile_{f['id']}"
            )])
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="renamecancel")])

        await update.message.reply_text(
            f"🎬 *{movie['title']}* ({movie['year'] or 'N/A'})\n\nWhat do you want to rename?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    for show in shows:
        kb = [
            [InlineKeyboardButton("✏️ Rename Title", callback_data=f"renametitle_show_{show['id']}")],
            [InlineKeyboardButton("📁 Edit Episode Quality", callback_data=f"renamebrowse_show_{show['id']}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="renamecancel")]
        ]

        await update.message.reply_text(
            f"📺 *{show['title']}*\n\nWhat do you want to rename?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )


async def handle_rename(update, context):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data == "renamecancel":
        await q.message.edit_text("❌ Rename cancelled.")
        return

    if data.startswith("renametitle_movie_"):
        movie_id = int(data.rsplit("_", 1)[1])
        context.user_data["rename_action"] = {"type": "movie_title", "id": movie_id}
        await q.message.edit_text("✏️ Reply with the new *title* for this movie.", parse_mode="Markdown")
        return

    if data.startswith("renametitle_show_"):
        show_id = int(data.rsplit("_", 1)[1])
        context.user_data["rename_action"] = {"type": "show_title", "id": show_id}
        await q.message.edit_text("✏️ Reply with the new *title* for this show.", parse_mode="Markdown")
        return

    if data.startswith("renamequality_moviefile_"):
        file_id = int(data.rsplit("_", 1)[1])
        context.user_data["rename_action"] = {"type": "movie_quality", "id": file_id}
        await q.message.edit_text(
            "✏️ Reply with the new *quality* (e.g. 720p, 1080p, 2160p).",
            parse_mode="Markdown"
        )
        return

    if data.startswith("renamequality_epfile_"):
        file_id = int(data.rsplit("_", 1)[1])
        context.user_data["rename_action"] = {"type": "episode_quality", "id": file_id}
        await q.message.edit_text(
            "✏️ Reply with the new *quality* (e.g. 720p, 1080p, 2160p).",
            parse_mode="Markdown"
        )
        return

    if data.startswith("renamebrowse_show_"):
        show_id = int(data.rsplit("_", 1)[1])
        seasons = fetchall("SELECT * FROM seasons WHERE show_id=? ORDER BY season_number", (show_id,))

        if not seasons:
            await q.message.edit_text("ℹ️ No seasons found for this show.")
            return

        kb = [
            [InlineKeyboardButton(f"Season {s['season_number']}", callback_data=f"renamebrowse_season_{s['id']}")]
            for s in seasons
        ]
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="renamecancel")])

        await q.message.edit_text("📁 Select a season:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("renamebrowse_season_"):
        season_id = int(data.rsplit("_", 1)[1])
        episodes = fetchall("SELECT * FROM episodes WHERE season_id=? ORDER BY episode_number", (season_id,))

        if not episodes:
            await q.message.edit_text("ℹ️ No episodes found for this season.")
            return

        kb = [
            [InlineKeyboardButton(f"Episode {e['episode_number']}", callback_data=f"renamebrowse_episode_{e['id']}")]
            for e in episodes
        ]
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="renamecancel")])

        await q.message.edit_text("📁 Select an episode:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("renamebrowse_episode_"):
        episode_id = int(data.rsplit("_", 1)[1])
        files = fetchall("SELECT * FROM episode_files WHERE episode_id=?", (episode_id,))

        if not files:
            await q.message.edit_text("ℹ️ No quality files found for this episode.")
            return

        kb = []
        for f in files:
            label = f"✏️ Quality: {f['quality']}"
            if f["part"]:
                label += f" (Part {f['part']})"
            kb.append([InlineKeyboardButton(label, callback_data=f"renamequality_epfile_{f['id']}")])
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="renamecancel")])

        await q.message.edit_text("📁 Select a file to change quality:", reply_markup=InlineKeyboardMarkup(kb))
        return


async def handle_rename_reply(update, context):
    """
    Generic text-message handler. Only acts if the admin is mid-rename
    (context.user_data['rename_action'] was set by a button tap above).
    Ignores all other plain text so it never interferes with anything else.
    """
    action = context.user_data.get("rename_action")
    if not action:
        return

    if not is_admin(update):
        return

    new_value = update.message.text.strip()
    context.user_data.pop("rename_action", None)

    if not new_value:
        await update.message.reply_text("❌ Value can't be empty. Rename cancelled.")
        return

    if action["type"] == "movie_title":
        execute("UPDATE movies SET title=? WHERE id=?", (new_value, action["id"]))
        await update.message.reply_text(f"✅ Movie title updated to *{new_value}*.", parse_mode="Markdown")

    elif action["type"] == "show_title":
        execute("UPDATE shows SET title=? WHERE id=?", (new_value, action["id"]))
        await update.message.reply_text(f"✅ Show title updated to *{new_value}*.", parse_mode="Markdown")

    elif action["type"] == "movie_quality":
        row = fetchall("SELECT * FROM movie_files WHERE id=?", (action["id"],))
        if not row:
            await update.message.reply_text("❌ File not found — it may have been deleted.")
            return

        movie_id = row[0]["movie_id"]
        dup = fetchall(
            "SELECT id FROM movie_files WHERE movie_id=? AND quality=? AND id!=?",
            (movie_id, new_value, action["id"])
        )
        if dup:
            await update.message.reply_text(
                f"❌ This movie already has a *{new_value}* file. Delete it first or pick a different quality.",
                parse_mode="Markdown"
            )
            return

        execute("UPDATE movie_files SET quality=? WHERE id=?", (new_value, action["id"]))
        await update.message.reply_text(f"✅ Quality updated to *{new_value}*.", parse_mode="Markdown")

    elif action["type"] == "episode_quality":
        row = fetchall("SELECT * FROM episode_files WHERE id=?", (action["id"],))
        if not row:
            await update.message.reply_text("❌ File not found — it may have been deleted.")
            return

        episode_id = row[0]["episode_id"]
        part = row[0]["part"]
        dup = fetchall(
            "SELECT id FROM episode_files WHERE episode_id=? AND quality=? AND part IS ? AND id!=?",
            (episode_id, new_value, part, action["id"])
        )
        if dup:
            await update.message.reply_text(
                f"❌ This episode already has a *{new_value}* file. Delete it first or pick a different quality.",
                parse_mode="Markdown"
            )
            return

        execute("UPDATE episode_files SET quality=? WHERE id=?", (new_value, action["id"]))
        await update.message.reply_text(f"✅ Quality updated to *{new_value}*.", parse_mode="Markdown")


async def format_guide(update, context):
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    await update.message.reply_text(
        "📋 *Filename Format Guide*\n\n"
        "*Movies:*\n"
        "`The.Dark.Knight.2008.720p.mkv`\n\n"
        "*Shows (Single Episode):*\n"
        "`Star.Wars.The.Clone.Wars.S07E11.720p.mkv`\n\n"
        "*Shows (Double Episode):*\n"
        "`Star.Wars.The.Bad.Batch.S02E16E17.1080p.mkv`\n\n"
        "*Qualities supported:*\n"
        "`480p | 720p | 1080p | 2160p | 4k`",
        parse_mode="Markdown"
    )


async def handle_photo(update, context):
    if not is_admin(update):
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id

    await update.message.reply_text(
        f"Photo file id:\n{file_id}"
    )


async def handle_channel_post(update, context):
    message = update.channel_post

    if not message:
        return

    if message.chat.id != CHANNEL_ID:
        return

    doc = message.document or message.video
    if not doc:
        return

    file_name = doc.file_name or "unknown"
    file_id = doc.file_id

    parsed = parse(file_name)

    if not parsed.get("valid"):
        await context.bot.send_message(
            ADMIN_ID,
            f"⚠️ Could not parse filename:\n`{file_name}`\n\n"
            f"Reason: {parsed.get('reason', 'Unknown')}",
            parse_mode="Markdown"
        )
        return

    added = add(parsed, file_id, file_name)

    if added:
        if parsed["type"] == "movie":
            info = f"🎬 *{parsed['title']}* ({parsed.get('year', 'N/A')}) — {parsed.get('quality', 'unknown')}"
        else:
            s = parsed.get("season")
            e1 = parsed.get("episode_start")
            e2 = parsed.get("episode_end")
            if e2:
                info = f"📺 *{parsed['title']}* — S{s:02d}E{e1:02d}E{e2:02d} — {parsed.get('quality', 'unknown')}"
            else:
                info = f"📺 *{parsed['title']}* — S{s:02d}E{e1:02d} — {parsed.get('quality', 'unknown')}"

        await context.bot.send_message(
            ADMIN_ID,
            f"✅ Detected and staged:\n{info}\n\nSend /done to save to database.",
            parse_mode="Markdown"
        )


async def activity(update, context):
    """
    Admin-only command: shows the most recent user activity
    (downloads, access requests, etc.) from the activity_log table.
    Usage: /activity [count]   (defaults to 20)

    Uses parse_mode="HTML" instead of Markdown. Logged titles/filenames
    can contain characters like _ * ` that break Telegram's Markdown
    parser and silently kill the whole message. HTML mode is safe here
    because every dynamic value is escaped with html.escape() before
    being inserted — only the static <b>/<code> tags are real markup.
    """
    if not is_admin(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    limit = 20
    if context.args:
        try:
            limit = max(1, min(int(context.args[0]), 100))
        except ValueError:
            await update.message.reply_text("❌ Invalid number. Usage: /activity 20")
            return

    rows = get_recent_activity(limit)

    if not rows:
        await update.message.reply_text("ℹ️ No activity logged yet.")
        return

    lines = [f"📜 <b>Last {len(rows)} Activity Log Entries:</b>\n"]
    for r in rows:
        ts = datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M")
        detail = f" — {html.escape(r['detail'])}" if r["detail"] else ""
        action = html.escape(r["action"])
        lines.append(f"• <code>{r['user_id']}</code> | {action}{detail} | {ts}")

    text = "\n".join(lines)

    # Telegram messages have a ~4096 char limit; trim safely if needed.
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(truncated, request a smaller count)"

    await update.message.reply_text(text, parse_mode="HTML")
