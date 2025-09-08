# Discord Bot Skeleton (Python + SQLite)

This repository contains a minimal, ready-to-run skeleton for a Discord bot built with Python, using SQLite for persistence.

## Features
- Structured project layout
- Environment-based configuration (via `.env`)
- Graceful startup/shutdown hooks
- Command prefix bot using `discord.py`
- Example command (`!ping`) and example user notes feature stored in SQLite
- Simple database layer with migrations on startup

## Quickstart

1. Create and activate a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
   COMMAND_PREFIX=!
   ```
4. Run the bot:
   ```bash
   python -m bot
   ```

## Project Structure
- `bot/__main__.py`: Entry point for running `python -m bot`
- `bot/config.py`: Loads configuration from environment variables
- `bot/db.py`: SQLite connection and simple migration
- `bot/bot.py`: Bot client and event/command registration
- `bot/cogs/notes.py`: Example cog demonstrating SQLite usage

## Notes
- Make sure to enable the necessary Gateway Intents for your bot in the Discord Developer Portal and adjust `bot.py` if needed.
- This skeleton keeps things minimal; extend as needed.
