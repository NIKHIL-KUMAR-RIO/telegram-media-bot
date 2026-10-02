# Telegram Media Bot

A self-hosted Telegram bot that turns a private channel into a personal
movie and TV archive — upload a file once, and approved users can browse
and pull it up again anytime through a simple button menu.

No external server, no paid storage. Telegram hosts the files; this bot
just keeps track of what's where and who's allowed to see it.

## How It Works

1. **Upload** a movie or episode to a private Telegram channel.
2. The bot **detects it automatically** and parses the filename — title,
   year or season/episode, quality — or asks for the details manually if
   the filename doesn't match a known pattern.
3. Approved users open the bot and **browse** Movies or Shows through an
   inline button menu: pick a title, pick a quality, done.
4. Sent files **auto-delete** from the chat after a set delay, so the
   channel history stays clean.

## Highlights

- Automatic filename parsing with a guided manual-entry fallback
- Access control: users request access, the admin approves or rejects
- Crash-safe — detected files are saved immediately, so a restart never
  loses anything mid-upload
- Full season sending, a random-pick option, and a custom watch order
- Admin tools for renaming, deleting, backing up, and reviewing activity

## Documentation

- **[PROJECT.md](PROJECT.md)** — full setup instructions, the complete
  filename format reference, every admin/user command, and the project's
  file structure
- **[AUTOSTART.md](AUTOSTART.md)** — turning this into an always-on
  background service that launches silently on Windows startup

## License

See [LICENSE](LICENSE) for details.
