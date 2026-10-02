# Running the Bot as a Permanent Background Service (Windows)

This turns a laptop into always-on hosting for the bot: compile it into a single
silent `.exe`, then launch that `.exe` automatically whenever Windows boots.
No terminal window, no manual `python bot.py`, nothing visible on the desktop.

This is separate from the [Setup](PROJECT.md#setup) steps in `PROJECT.md`,
which cover running the bot normally for development. Use this guide once the
bot works and you want it to run permanently in the background.

## 1. Project Directory Overview

Before compiling, your project root should look like this:

```
your-bot-project/
├── core/
├── handlers/
├── storage/
│   └── cache.db
├── .env
├── .env.example
├── .gitignore
├── bot.py
├── config.py
├── db.py
├── requirements.txt
└── schema.sql
```

`venv/`, `__pycache__/`, `build/`, and `dist/` aren't listed here — they get
generated during the steps below.

## 2. Environment Setup

Open Command Prompt or PowerShell in the project root:

```powershell
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies and PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# Set up your real environment values
copy .env.example .env
```

Fill in real tokens, keys, and IDs in `.env` before continuing.

## 3. Compile to a Silent Standalone Executable

```powershell
pyinstaller --onefile --noconsole bot.py
```

| Flag | What it does |
|---|---|
| `--onefile` | Packages the interpreter, bytecode, and dependencies into a single `bot.exe` |
| `--noconsole` | Suppresses the black terminal window, so the process runs silently in the background |

This creates a `build/` folder, a `dist/` folder, and a `bot.spec` file.

## 4. Assemble Runtime Assets in `dist/`

PyInstaller bundles your Python code, but it doesn't bundle files your bot
reads at runtime. **Copy** (don't move) these into `dist/`, next to `bot.exe`:

- `.env`
- `schema.sql`
- `storage/` (including `cache.db`, if it already exists)

`dist/` should end up looking like this:

```
dist/
├── bot.exe
├── .env
├── schema.sql
└── storage/
    └── cache.db
```

Once you've confirmed `bot.exe` runs correctly from `dist/`, you can delete
the `build/` folder to free up space. Leave the root project files alone —
you'll still edit and test from there in VS Code.

## 5. Configure Auto-Start on Windows Boot

1. Open the `dist/` folder in File Explorer.
2. Right-click `bot.exe` → **Show more options** → **Create shortcut**.
3. Press `Win + R`, type `shell:startup`, and hit Enter. This opens your
   Startup folder.
4. Cut and paste the new `bot.exe - Shortcut` into that Startup folder.

From now on, the bot launches automatically and silently every time you sign
in to Windows — no cmd window, nothing on the desktop.

## 6. Managing the Background Process

Because it runs with `--noconsole`, there's no window to click into or close.

**Check if it's running:**
- Task Manager (`Ctrl + Shift + Esc`) → **Details** tab → look for `bot.exe`
- Or from a terminal:
  ```powershell
  tasklist | findstr /i "bot.exe"
  ```

**Stop it before testing changes in VS Code.** Running the compiled `bot.exe`
and a `python bot.py` instance at the same time causes a Telegram API
conflict (both are polling with the same bot token). Kill the background
instance first:

```powershell
taskkill /f /im bot.exe
```

When you're done testing in VS Code, re-launch `bot.exe` from `dist/` (or
just reboot) to go back to the always-on background setup.

## 7. Updating the Bot Later

The compiled `bot.exe` is a snapshot — editing `bot.py` in the root project
doesn't change it. To ship a code update to the always-on version:

1. Stop the running `bot.exe` (`taskkill /f /im bot.exe`).
2. Re-run `pyinstaller --onefile --noconsole bot.py` from the root.
3. Replace the old `bot.exe` in `dist/` with the new one.
4. Relaunch it (or reboot).

## 8. `.gitignore` Checklist

This workflow creates extra files that should never reach GitHub, on top of
what your repo's `.gitignore` already excludes (like `.env` and
`storage/*.db`). Make sure it also covers:

```gitignore
# PyInstaller build artifacts
build/
dist/
*.spec
```
