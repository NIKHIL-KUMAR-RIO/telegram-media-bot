import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MOVIES_POSTER = os.getenv("MOVIES_POSTER")
SHOWS_POSTER = os.getenv("SHOWS_POSTER")
MAIN_POSTER = os.getenv("MAIN_POSTER")