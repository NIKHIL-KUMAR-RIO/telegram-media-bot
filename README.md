# Telegram Media Bot

A private Telegram bot for storing and sharing movies and TV shows. Files are uploaded to a private Telegram channel, the bot detects them, parses the filename (with a manual-entry fallback for anything it can't auto-parse), and makes them available to approved users via an inline button menu.

## Features

- Auto-detects files uploaded to a private channel and parses filenames into structured data (title, year/season/episode, quality)
- Falls back to a guided manual-entry flow (Title → Year/Season/Episode → Quality) when a filename can't be auto-parsed
- User access whitelist with approve/reject buttons
- Media request system (users can request titles, admin approves/rejects)
- Delete media by name, with confirmation buttons
- Paginated navigation: movies (6/page), shows (6/page), seasons (5/page), episodes (6/page)
- Full season sending, random pick, and a `/watchorder` command for a custom chronological viewing order
- Crash-safe staging — detected files are saved to the database immediately, so a bot restart never loses them

## Setup

1. Clone this repo
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Linux/Mac
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your real values:
   ```
   BOT_TOKEN=       # from @BotFather
   ADMIN_ID=        # your Telegram numeric user ID
   CHANNEL_ID=      # your private channel's ID
   MOVIES_POSTER=   # file_id of a poster image for the Movies menu
   SHOWS_POSTER=    # file_id of a poster image for the Shows menu
   MAIN_POSTER=     # file_id of a poster image for the main menu
   ```
4. Run the bot:
   ```
   python bot.py
   ```

## Filename Format

The bot tries several formats automatically, in this order:

```
Movies:
The.Dark.Knight.2008.1080p.mkv
The Matrix (1999) 1080p.mkv
Movie Title [2008] 720p.mkv

Shows:
Star.Wars.The.Clone.Wars.S07E11.720p.mkv       (standard)
Star.Wars.The.Bad.Batch.S02E16E17.1080p.mkv    (double episode)
Breaking Bad 1x05 720p.mkv                      (alt format)
Show Title Season 2 Episode 5.mkv               (wordy format)

Qualities supported: 480p | 720p | 1080p | 2160p | 4k
```

If a filename doesn't match any of these, the bot asks the admin to enter the details manually via chat instead of rejecting the file.

## Admin Commands

| Command | Purpose |
|---|---|
| `/done` | Save all staged files to the database |
| `/delete <name>` | Delete a movie or show by name (with confirmation) |
| `/approve <id>` | Approve a user by Telegram ID |
| `/revoke <id>` | Revoke a user's access |
| `/users` | List all approved users |
| `/format` | Show the filename format guide |

## User Commands

| Command | Purpose |
|---|---|
| `/start` | Open the main menu |
| `/watchorder` | Show the chronological watch order |
| `/request <text>` | Send a media request to the admin |

## Project Structure

```
telegram-media-bot/
├── bot.py               ← Entry point, registers all handlers
├── db.py                ← Database connection and query helpers
├── schema.sql            ← Database schema
├── config.py             ← Loads environment variables
├── requirements.txt       ← Python dependencies
│
├── core/
│   ├── parser.py          ← Parses filenames into structured data
│   ├── staging.py          ← Writes detected files to the staging table
│   ├── approval.py          ← Moves staged files into the real tables
│   ├── sender.py            ← Sends files to users
│   └── locks.py              ← Prevents duplicate sends per user
│
└── handlers/
    ├── start.py             ← /start command, access control
    ├── navigation.py         ← Inline button navigation, /watchorder
    └── admin.py               ← Admin commands, channel detection, manual entry
```

## Notes

- Requires `python-telegram-bot==22.8` and `python-dotenv`
- Uses Telegram's own servers for file storage — no local media storage
- SQLite database lives at `storage/cache.db` (not committed — see `.gitignore`)
- `.env` holds real secrets and is never committed — use `.env.example` as a template
