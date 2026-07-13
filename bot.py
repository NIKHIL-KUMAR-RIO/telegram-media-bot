import logging
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, CHANNEL_ID, ADMIN_ID
from db import init_db
from handlers.start import start
from handlers.navigation import handle_callback, watchorder
from handlers.admin import done, approve, revoke, list_users, handle_channel_post, handle_access_request, format_guide, handle_photo, media_request, handle_media_request, delete_media, handle_delete

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def set_commands(app):
    # Commands visible to all users
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Open main menu"),
            BotCommand("watchorder", "Show Star Wars watch order"),
            BotCommand("request", "Send a media request"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )
    # Commands visible only to admin
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Open main menu"),
            BotCommand("watchorder", "Show Star Wars watch order"),
            BotCommand("request", "Send a media request"),
            BotCommand("done", "Save staged files"),
            BotCommand("delete", "Delete media by name"),
            BotCommand("approve", "Approve a user"),
            BotCommand("revoke", "Revoke a user"),
            BotCommand("users", "List approved users"),
            BotCommand("format", "Show filename format guide"),
        ],
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Set commands on startup
    app.post_init = set_commands

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("watchorder", watchorder))
    app.add_handler(CommandHandler("request", media_request))

    # Admin commands
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("delete", delete_media))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("revoke", revoke))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("format", format_guide))

    # Channel post handler
    app.add_handler(MessageHandler(filters.Chat(chat_id=CHANNEL_ID), handle_channel_post))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Access request callbacks
    app.add_handler(CallbackQueryHandler(handle_access_request, pattern="^(requestaccess_|grantaccess_|rejectaccess_)"))

    # Media request callbacks
    app.add_handler(CallbackQueryHandler(handle_media_request, pattern="^(approverequest_|rejectrequest_)"))

    # Delete callbacks
    app.add_handler(CallbackQueryHandler(handle_delete, pattern="^(delmovie_|delshow_|delseason_|delcancel)"))

    # Navigation callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Error handler
    async def error_handler(update, context):
        logger.warning(f"Network error occurred: {context.error}")

    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
