from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import fetchall
from config import ADMIN_ID, MAIN_POSTER


def is_approved(user_id):
    row = fetchall("SELECT * FROM approved_users WHERE user_id=?", (user_id,))
    return len(row) > 0


async def start(update, context):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    if user_id == ADMIN_ID or is_approved(user_id):
        kb = [
            [
                InlineKeyboardButton("🎬 Movies", callback_data="movies"),
                InlineKeyboardButton("📺 Shows", callback_data="shows")
            ],
            [
                InlineKeyboardButton("🎲 Random from the Galaxy", callback_data="random")
            ]
        ]

        await update.message.reply_photo(
            photo=MAIN_POSTER,
            caption=(
                f"⭐ The Galactic Archive\n\n"
                f"A long time ago in a galaxy far, far away...\n"
                f"Your Star Wars collection awaits, {first_name}."
            ),
            reply_markup=InlineKeyboardMarkup(kb)
        )

    else:
        kb = [
            [InlineKeyboardButton("📨 Request Access", callback_data=f"requestaccess_{user_id}")]
        ]

        await update.message.reply_text(
            f"👋 Hello {first_name}!\n\n"
            "⛔ You don't have access to this bot yet.\n\n"
            f"Your Telegram ID is: `{user_id}`\n"
            "Tap the button below to request access from the admin.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
