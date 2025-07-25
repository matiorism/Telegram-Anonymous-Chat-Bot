import os

# These values will be read from the secrets you set in your Cloudflare Worker settings.

# CRITICAL: Your Telegram Bot Token. The script will fail if this is not set.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Your bot's username
BOT_ID = os.getenv("BOT_ID", "USERNAME")

# Set to "ALL" or a comma-separated list of usernames. Defaults to "ALL".
ALLOWED = os.getenv("ALLOWED", "ALL")

# --- Derived Configuration ---
# This is derived automatically from your bot token.
BOT_TELEGRAM_ID = BOT_TOKEN.split(':')[0] if BOT_TOKEN else ""
