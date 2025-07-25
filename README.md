# Anonymous Telegram Chat Bot for Cloudflare Workers

This repository contains the source code for a serverless Telegram bot that allows users to receive and reply to anonymous messages. It is built to run on the [Cloudflare Workers](https://workers.cloudflare.com/) platform, using Python, Cloudflare D1 for the database, and the Telegram Bot API.

This project is structured with a separate configuration file (`config.py`) for easy management of settings through environment variables (secrets).

## 🌟 Features

  - **Anonymous Messaging**: Users get a personal, shareable link. Anyone with the link can send them anonymous messages.
  - **Direct Replies**: Users can directly reply to the anonymous messages they receive, and the bot will forward the reply to the original sender.
  - **Block/Unblock**: Recipients can block any sender to stop receiving messages from them.
  - **Multi-Language Support**: The bot interface is available in English and Persian (Farsi).
  - **Serverless**: Runs entirely on Cloudflare's serverless infrastructure, requiring no dedicated server.
  - **Secure & Private**: Configuration is handled via environment secrets. Sender information is obfuscated in callbacks.
  - **Rate Limiting**: Basic protection against spam and abuse.

## 🤔 How It Works

1.  **Get Your Link**: A user starts the bot and requests their unique anonymous link. The bot generates a link like `https://t.me/YourBotUsername?start=uniquekey`.
2.  **Share the Link**: The user shares this link on their social media or with friends.
3.  **Send an Anonymous Message**: Another person clicks the link. They are taken to the bot and prompted to send their message.
4.  **Receive the Message**: The bot forwards this message to the link's owner without revealing the sender. The message includes a "Block Sender" button.
5.  **Reply in Secret**: The recipient can reply to the message directly in their Telegram chat. The bot catches this reply and forwards it back to the original anonymous sender.

The bot uses a Cloudflare D1 database to map message IDs, which ensures that replies are sent to the correct person.

## 🚀 Deployment Guide

This bot is designed to be deployed on Cloudflare Workers.

### Prerequisites

  - A [Cloudflare account](https://www.google.com/search?q=https://dash.cloudflare.com/sign-up).
  - The [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed on your machine.
  - A Telegram Bot Token from [@BotFather](https://t.me/BotFather).

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

The project contains two main files: `entry.py` (the bot's logic) and `config.py` (for handling settings).

### Step 2: Create a Telegram Bot

1.  Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2.  Create a new bot by sending the `/newbot` command.
3.  Follow the instructions. BotFather will give you a **Bot Token**.
4.  Optionally, set a username for your bot (e.g., `MyAnonymousBot`).

### Step 3: Set Up Cloudflare D1 Database

1.  Create a D1 database in your Cloudflare dashboard or via Wrangler:

    ```bash
    wrangler d1 create anonymous-bot-db
    ```

2.  Run the following commands to create the necessary tables. Replace `anonymous-bot-db` with your database name.

    ```bash
    # Create the 'users' table
    wrangler d1 execute anonymous-bot-db --command "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_user_id TEXT NOT NULL UNIQUE, rkey TEXT NOT NULL, language TEXT DEFAULT 'en', target_user TEXT);"

    # Create the 'blocked_users' table
    wrangler d1 execute anonymous-bot-db --command "CREATE TABLE blocked_users (blocker_id TEXT NOT NULL, blocked_id TEXT NOT NULL, PRIMARY KEY (blocker_id, blocked_id));"

    # Create the 'message_mappings' table
    wrangler d1 execute anonymous-bot-db --command "CREATE TABLE message_mappings (original_message_id TEXT, original_chat_id TEXT, forwarded_message_id TEXT, forwarded_chat_id TEXT, sender_id TEXT, receiver_id TEXT, PRIMARY KEY (forwarded_message_id, forwarded_chat_id));"
    ```

### Step 4: Configure `wrangler.toml`

Create a `wrangler.toml` file in the root of your project. **Note the `main` entry point is `entry.py`**.

```toml
name = "telegram-anonymous-bot"
main = "entry.py"
compatibility_date = "2024-03-14"

# D1 Database binding
[[d1_databases]]
binding = "DB"
database_name = "anonymous-bot-db"
database_id = "<your-d1-database-id>" # Get this from the Cloudflare dashboard
```

### Step 5: Set Up Configuration (Secrets)

Your bot's configuration is loaded from secrets set in your Cloudflare Worker. This keeps your tokens and settings secure.

1.  **Set the mandatory Bot Token:**

    ```bash
    wrangler secret put BOT_TOKEN
    # Paste your token from BotFather when prompted
    ```

2.  **Set optional configurations:**

    ```bash
    # Your bot's Telegram username (without the @)
    wrangler secret put BOT_ID
    # Enter the username, e.g., MyAnonymousBot

    # To restrict usage to certain usernames (optional)
    wrangler secret put ALLOWED
    # Enter a comma-separated list like "user1,user2"
    ```

    If `BOT_ID` and `ALLOWED` are not set, they will fall back to their default values ("WhoWouldBe" and "ALL", respectively).

### Step 6: Deploy the Worker

```bash
wrangler deploy
```

### Step 7: Set the Webhook

After deployment, tell Telegram where to send bot updates. Take your new worker URL (e.g., `https://telegram-anonymous-bot.your-username.workers.dev`) and visit the `/init` path in your browser.

`https://telegram-anonymous-bot.your-username.workers.dev/init`

This registers your worker's unique webhook URL with the Telegram API. Your bot is now live\!

## ⚙️ Configuration

The bot is configured via environment variables (secrets) which are loaded by `config.py`.

  - `BOT_TOKEN` (Required): Your Telegram bot token. The script will not run without it.
  - `BOT_ID` (Optional): Your bot's Telegram username. Defaults to `"WhoWouldBe"` if not set.
  - `ALLOWED` (Optional): Controls who can use the bot. Defaults to `"ALL"`.
      - Set to `"ALL"` to allow any Telegram user.
      - Set to a comma-separated string of Telegram usernames to create a whitelist (e.g., `"user1,user2"`).
