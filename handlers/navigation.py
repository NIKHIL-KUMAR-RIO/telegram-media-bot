import random as rnd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from db import fetchall, is_approved
from core.sender import send_movie, send_episode, send_season
from config import ADMIN_ID, MOVIES_POSTER, SHOWS_POSTER, MAIN_POSTER

EPISODES_PER_PAGE = 6
SEASONS_PER_PAGE = 5
SHOWS_PER_PAGE = 6
MOVIES_PER_PAGE = 6

STAR_WARS_ORDER = r"""⭐ *Chronological Order Of STAR WARS*

1. Young Jedi Adventures
2. The Acolyte
3. Episode I - The Phantom Menace
4. Tales of the Jedi E02 - Justice
5. Tales of the Jedi E03 - Choices
6. Tales of the Jedi E04 - The Sith Lord
7. Episode II - Attack of the Clones
8. Tales of the Jedi E01 - Life and Death
9. The Clone Wars (2008) - Film
10. The Clone Wars - Show
11. Tales of the Jedi E05 - Practice Makes Perfect
    _(Watch before: The Clone Wars S07E11 - Victory and Death)_
12. Tales of the Empire E01 - The Path of Fear
13. Episode III - Revenge of the Sith
14. Tales of the Empire E04 - Devoted
15. Tales of the Empire E05 - Realization
16. Tales of the Empire E06 - The Way Out
17. Tales of the Jedi E06 - Resolve
18. The Bad Batch (Complete)
19. Maul - Shadow Lord
20. Obi-Wan Kenobi
21. Solo: A Star Wars Story
22. Star Wars Rebels S01 - S02
23. Tales of the Empire E02 - The Path of Anger
24. Star Wars Rebels S03 - S04
25. Andor (Complete)
26. Rogue One: A Star Wars Story
27. Episode IV - A New Hope
28. Episode V - The Empire Strikes Back
29. Caravan of Courage: An Ewok Adventure \[1984\]
30. Ewoks \[1985\]
31. Episode VI - Return of the Jedi
32. The Mandalorian S01
33. Tales of the Empire E03 - The Path of Hate
34. The Mandalorian S02
35. The Book of Boba Fett
36. The Mandalorian S03
37. The Mandalorian and Grogu
38. Ahsoka
39. Skeleton Crew
40. Star Wars Resistance (Complete)
41. Episode VII - The Force Awakens
42. Episode VIII - The Last Jedi
43. Episode IX - The Rise of Skywalker

─────────────────────
🔴 *Non-Canon*
• Visions (2021)"""


async def watchorder(update, context):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID and not is_approved(user_id):
        await update.message.reply_text("⛔ You don't have access to this bot.")
        return

    await update.message.reply_text(
        STAR_WARS_ORDER,
        parse_mode="Markdown"
    )


async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()

    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    # Block non approved users
    if user_id != ADMIN_ID and not is_approved(user_id):
        await q.message.edit_text("⛔ You don't have access to this bot.")
        return

    bot = context.bot
    chat_id = q.message.chat_id
    data = q.data

    # -------------------------
    # MOVIES LIST
    # -------------------------
    if data == "movies" or data.startswith("moviepage_"):
        page = 0 if data == "movies" else int(data.split("_", 1)[1])

        rows = fetchall("SELECT * FROM movies ORDER BY order_index")

        if not rows:
            await q.message.edit_caption(
                "❌ No movies available yet.",
                reply_markup=_back_to_main()
            )
            return

        total = len(rows)
        total_pages = (total + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE
        start = page * MOVIES_PER_PAGE
        end = start + MOVIES_PER_PAGE
        page_items = rows[start:end]

        kb = [[InlineKeyboardButton(r["title"], callback_data=f"movie_{r['id']}")] for r in page_items]

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"moviepage_{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"moviepage_{page + 1}"))
        if nav:
            kb.append(nav)

        kb.append([InlineKeyboardButton("🔙 Back", callback_data="main")])

        page_label = f"Page {page + 1}/{total_pages} — " if total_pages > 1 else ""

        if data == "movies":
            await q.message.edit_media(
                media=InputMediaPhoto(media=MOVIES_POSTER, caption=f"🎬 {page_label}Select a movie:"),
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await q.message.edit_caption(
                f"🎬 {page_label}Select a movie:",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    # -------------------------
    # SHOWS LIST
    # -------------------------
    elif data == "shows" or data.startswith("showpage_"):
        page = 0 if data == "shows" else int(data.split("_", 1)[1])

        rows = fetchall("SELECT * FROM shows ORDER BY order_index")

        if not rows:
            await q.message.edit_caption(
                "❌ No shows available yet.",
                reply_markup=_back_to_main()
            )
            return

        total = len(rows)
        total_pages = (total + SHOWS_PER_PAGE - 1) // SHOWS_PER_PAGE
        start = page * SHOWS_PER_PAGE
        end = start + SHOWS_PER_PAGE
        page_items = rows[start:end]

        kb = [[InlineKeyboardButton(r["title"], callback_data=f"show_{r['id']}")] for r in page_items]

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"showpage_{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"showpage_{page + 1}"))
        if nav:
            kb.append(nav)

        kb.append([InlineKeyboardButton("🔙 Back", callback_data="main")])

        page_label = f"Page {page + 1}/{total_pages} — " if total_pages > 1 else ""

        if data == "shows":
            await q.message.edit_media(
                media=InputMediaPhoto(media=SHOWS_POSTER, caption=f"📺 {page_label}Select a show:"),
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await q.message.edit_caption(
                f"📺 {page_label}Select a show:",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    # -------------------------
    # RANDOM PICK
    # -------------------------
    elif data == "random":
        movies = fetchall("SELECT * FROM movies")
        shows = fetchall("SELECT * FROM shows")

        all_items = (
            [("movie", r) for r in movies] +
            [("show", r) for r in shows]
        )

        if not all_items:
            await q.message.edit_caption(
                "❌ No media available yet.",
                reply_markup=_back_to_main()
            )
            return

        kind, item = rnd.choice(all_items)

        if kind == "movie":
            kb = [
                [InlineKeyboardButton("📥 Download", callback_data=f"movie_{item['id']}")],
                [InlineKeyboardButton("🎲 Pick Another", callback_data="random")],
                [InlineKeyboardButton("🔙 Back", callback_data="main")]
            ]

            await q.message.edit_caption(
                f"🎲 Random Pick!\n\n🎬 *{item['title']}* ({item['year'] or 'N/A'})",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )

        else:
            seasons = fetchall("SELECT * FROM seasons WHERE show_id=? ORDER BY season_number", (item["id"],))
            kb = [
                [InlineKeyboardButton(f"Season {s['season_number']}", callback_data=f"season_{s['id']}_{item['id']}")]
                for s in seasons
            ]
            kb.append([InlineKeyboardButton("🎲 Pick Another", callback_data="random")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="main")])

            await q.message.edit_caption(
                f"🎲 Random Pick!\n\n📺 *{item['title']}*\n\nSelect a season:",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )

    # -------------------------
    # SEND MOVIE FILE
    # -------------------------
    elif data.startswith("movie_"):
        movie_id = int(data.split("_", 1)[1])

        await q.message.edit_caption("⏳ Sending movie, please wait...")
        await send_movie(bot, chat_id, movie_id)
        await q.message.edit_caption(
            "📥 Done — check below for your file.",
            reply_markup=_back_to_movies()
        )

    # -------------------------
    # SHOW SEASONS LIST
    # -------------------------
    elif data.startswith("show_") or data.startswith("seasonpage_"):
        if data.startswith("show_"):
            show_id = int(data.split("_", 1)[1])
            page = 0
        else:
            parts = data.split("_", 2)
            show_id = int(parts[1])
            page = int(parts[2])

        rows = fetchall(
            "SELECT * FROM seasons WHERE show_id=? ORDER BY season_number",
            (show_id,)
        )

        if not rows:
            await q.message.edit_caption(
                "❌ No seasons available for this show.",
                reply_markup=_back_to_shows()
            )
            return

        total = len(rows)
        total_pages = (total + SEASONS_PER_PAGE - 1) // SEASONS_PER_PAGE
        start = page * SEASONS_PER_PAGE
        end = start + SEASONS_PER_PAGE
        page_items = rows[start:end]

        kb = [
            [InlineKeyboardButton(f"Season {r['season_number']}", callback_data=f"season_{r['id']}_{show_id}")]
            for r in page_items
        ]

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"seasonpage_{show_id}_{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"seasonpage_{show_id}_{page + 1}"))
        if nav:
            kb.append(nav)

        kb.append([InlineKeyboardButton("🔙 Back", callback_data="shows")])

        page_label = f"Page {page + 1}/{total_pages} — " if total_pages > 1 else ""
        await q.message.edit_caption(f"📺 {page_label}Select a season:", reply_markup=InlineKeyboardMarkup(kb))

    # -------------------------
    # SEASON EPISODES LIST (with pagination)
    # -------------------------
    elif data.startswith("season_") or data.startswith("eppage_"):

        if data.startswith("season_"):
            parts = data.split("_", 2)
            season_id = int(parts[1])
            show_id = int(parts[2])
            page = 0
        else:
            parts = data.split("_", 3)
            season_id = int(parts[1])
            show_id = int(parts[2])
            page = int(parts[3])

        rows = fetchall(
            "SELECT * FROM episodes WHERE season_id=? ORDER BY episode_number",
            (season_id,)
        )

        if not rows:
            await q.message.edit_caption(
                "❌ No episodes available for this season.",
                reply_markup=_back_to_shows()
            )
            return

        # Group consecutive episodes that share the same file_id
        grouped = []
        skip = set()

        for i, ep in enumerate(rows):
            if ep["id"] in skip:
                continue

            ep_files = fetchall(
                "SELECT * FROM episode_files WHERE episode_id=?", (ep["id"],)
            )

            if i + 1 < len(rows):
                next_ep = rows[i + 1]
                next_files = fetchall(
                    "SELECT * FROM episode_files WHERE episode_id=?", (next_ep["id"],)
                )
                if (ep_files and next_files and
                        ep_files[0]["file_id"] == next_files[0]["file_id"]):
                    label = f"Episode {ep['episode_number']}-{next_ep['episode_number']}"
                    grouped.append((label, ep["id"]))
                    skip.add(next_ep["id"])
                    continue

            grouped.append((f"Episode {ep['episode_number']}", ep["id"]))

        # Paginate
        total = len(grouped)
        total_pages = (total + EPISODES_PER_PAGE - 1) // EPISODES_PER_PAGE
        start = page * EPISODES_PER_PAGE
        end = start + EPISODES_PER_PAGE
        page_items = grouped[start:end]

        kb = [
            [InlineKeyboardButton(label, callback_data=f"episode_{ep_id}_{season_id}_{show_id}")]
            for label, ep_id in page_items
        ]

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"eppage_{season_id}_{show_id}_{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"eppage_{season_id}_{show_id}_{page + 1}"))
        if nav:
            kb.append(nav)

        if page == 0:
            kb.append([InlineKeyboardButton("📥 Send Full Season", callback_data=f"getseason_{season_id}_{show_id}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data=f"show_{show_id}")])

        page_label = f"Page {page + 1}/{total_pages} — " if total_pages > 1 else ""
        await q.message.edit_caption(
            f"📺 {page_label}Select an episode:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # -------------------------
    # SEND EPISODE FILE
    # -------------------------
    elif data.startswith("episode_"):
        parts = data.split("_", 3)
        episode_id = int(parts[1])
        season_id = int(parts[2])
        show_id = int(parts[3])

        await q.message.edit_caption("⏳ Sending episode, please wait...")
        await send_episode(bot, chat_id, episode_id)
        await q.message.edit_caption(
            "📥 Done — check below for your file.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data=f"season_{season_id}_{show_id}")]]
            )
        )

    # -------------------------
    # SEND FULL SEASON
    # -------------------------
    elif data.startswith("getseason_"):
        parts = data.split("_", 2)
        season_id = int(parts[1])
        show_id = int(parts[2])

        await q.message.edit_caption("⏳ Sending full season, please wait...")
        await send_season(bot, chat_id, season_id)
        await q.message.edit_caption(
            "📥 Done — check below for your files.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data=f"season_{season_id}_{show_id}")]]
            )
        )

    # -------------------------
    # BACK TO MAIN MENU
    # -------------------------
    elif data == "main":
        kb = [
            [
                InlineKeyboardButton("🎬 Movies", callback_data="movies"),
                InlineKeyboardButton("📺 Shows", callback_data="shows")
            ],
            [
                InlineKeyboardButton("🎲 Random from the Galaxy", callback_data="random")
            ]
        ]
        await q.message.edit_media(
            media=InputMediaPhoto(
                media=MAIN_POSTER,
                caption=(
                    f"⭐ The Galactic Archive\n\n"
                    f"A long time ago in a galaxy far, far away...\n"
                    f"Your Star Wars collection awaits, {first_name}."
                )
            ),
            reply_markup=InlineKeyboardMarkup(kb)
        )


# -------------------------
# HELPER KEYBOARDS
# -------------------------
def _back_to_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main")]])


def _back_to_movies():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="movies")]])


def _back_to_shows():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="shows")]])
