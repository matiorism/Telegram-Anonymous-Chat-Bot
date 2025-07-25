from workers import Response, handler
from js import Object, fetch
import hashlib, json, re, random, string, base64
import asyncio
import logging
from typing import Optional, Dict
from urllib.parse import urlparse

from config import BOT_TOKEN, BOT_ID, BOT_TELEGRAM_ID

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

BOT_TELEGRAM_ID = BOT_TOKEN.split(':')[0]

# In-memory storage for rate limiting. For production, consider using a persistent store like Redis.
rate_limit_storage = {}

# 2. LANGUAGE STRINGS
LANGUAGES = {
    "fa": {
        "WELCOME": "🎉 خوش آمدید به بات پیام ناشناس!\n\nبرای شروع از دکمه زیر استفاده کنید.",
        "GUIDE_BUTTON": "💡 راهنما",
        "NEW_LINK_BUTTON": "🔗 لینک ناشناس من",
        "LANG_BUTTON": "🇬🇧 English",
        "CANCEL_BUTTON": "❌ لغو",
        "GUIDE_TEXT": "برای پاسخ دادن، کافیست روی پیام مورد نظر ریپلای کرده و جواب خود را بنویسید.",
        "LINK_GENERATED": "🔗 *لینک ناشناس شما:*\n\n`{}`\n\n💡 این لینک را برای دیگران بفرستید تا بتوانند برای شما پیام ناشناس ارسال کنند\\.",
        "START_REPLY": "✅ در حال ارسال پیام به {} هستی.\n\nهرچی بفرستی ناشناس میره براش. میتونی متن، ویس یا هرچی خواستی بفرستی.",
        "INVALID_LINK": "❌ لینک نامعتبر یا منقضی شده",
        "NO_TARGET": "❌ شما در حال حاضر به کسی متصل نیستید.\n\nبرای ارسال پیام ناشناس، از لینک کسی استفاده کنید یا لینک خود را بسازید.",
        "MESSAGE_SENT": "✅ پیام شما به صورت ناشناس ارسال شد.",
        "MESSAGE_BLOCKED": "❌ این کاربر شما را مسدود کرده است.",
        "REPLY_SENT": "✅ پاسخ شما ارسال شد.",
        "REPLY_BLOCKED": "❌ شما توسط این کاربر مسدود شده اید.",
        "SEND_ERROR": "❌ خطا در ارسال پیام: {}",
        "REPLY_ERROR": "❌ خطا در ارسال پاسخ.",
        "USER_BLOCKED_BOT": "❌ کاربر مقصد ربات را مسدود کرده یا در دسترس نیست.",
        "USER_CREATION_ERROR": "❌ خطا در ایجاد حساب کاربری. لطفا دوباره تلاش کنید.",
        "RATE_LIMIT": "⚠️ شما خیلی سریع پیام میفرستید. لطفا کمی صبر کنید.",
        "USER_BLOCKED": "✅ کاربر مسدود شد",
        "USER_UNBLOCKED": "✅ کاربر آنبلاک شد",
        "BLOCK_BUTTON": "🚫 بلاک کردن فرستنده",
        "UNBLOCK_BUTTON": "🔓 آنبلاک فرستنده",
        "BLOCK_ERROR": "❌ خطا در بلاک کردن",
        "UNBLOCK_ERROR": "❌ خطا در آنبلاک کردن",
        "LANG_SET": "زبان به فارسی تغییر کرد.",
        "CANCEL_SUCCESS": "✅ ارسال پیام لغو شد."
    },
    "en": {
        "WELCOME": "🎉 Welcome to the Anonymous Message Bot!\n\nUse the buttons below to get started.",
        "GUIDE_BUTTON": "💡 Guide",
        "NEW_LINK_BUTTON": "🔗 My Anonymous Link",
        "LANG_BUTTON": "🇮🇷 فارسی",
        "CANCEL_BUTTON": "❌ Cancel",
        "GUIDE_TEXT": "To reply to a message, simply reply to it directly and write your message.",
        "LINK_GENERATED": "🔗 *Your anonymous link:*\n\n`{}`\n\n💡 Share this link with others so they can send you anonymous messages\\.",
        "START_REPLY": "✅ You are now sending a message to {}.\n\nAnything you send will be delivered anonymously. You can send text, voice messages, photos, etc.",
        "INVALID_LINK": "❌ Invalid or expired link.",
        "NO_TARGET": "❌ You are not currently connected to anyone.\n\nTo send an anonymous message, use someone's link or create your own.",
        "MESSAGE_SENT": "✅ Your message has been sent anonymously.",
        "MESSAGE_BLOCKED": "❌ This user has blocked you.",
        "REPLY_SENT": "✅ Your reply has been sent.",
        "REPLY_BLOCKED": "❌ You have been blocked by this user.",
        "SEND_ERROR": "❌ Error sending message: {}",
        "REPLY_ERROR": "❌ Error sending reply.",
        "USER_BLOCKED_BOT": "❌ The target user has blocked the bot or is unavailable.",
        "USER_CREATION_ERROR": "❌ Error creating user account. Please try again.",
        "RATE_LIMIT": "⚠️ You are sending messages too quickly. Please wait a moment.",
        "USER_BLOCKED": "✅ User blocked.",
        "USER_UNBLOCKED": "✅ User unblocked.",
        "BLOCK_BUTTON": "🚫 Block Sender",
        "UNBLOCK_BUTTON": "🔓 Unblock Sender",
        "BLOCK_ERROR": "❌ Error blocking user.",
        "UNBLOCK_ERROR": "❌ Error unblocking user.",
        "LANG_SET": "Language set to English.",
        "CANCEL_SUCCESS": "✅ Message sending canceled."
    }
}

def get_lang_string(lang_code, key):
    """Retrieves a string in the specified language."""
    return LANGUAGES.get(lang_code, LANGUAGES["en"]).get(key, key)

def to_js(obj):
    """Converts a Python dictionary to a JavaScript object."""
    from pyodide.ffi import to_js as _to_js
    return _to_js(obj, dict_converter=Object.fromEntries)

def rndKey() -> str:
    """Generates a random 16-character key."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))

def hxId(id_num: int) -> str:
    """Converts an integer ID to its hexadecimal representation."""
    return hex(id_num)[2:]

def revHxId(hxid: str) -> Optional[int]:
    """Converts a hexadecimal string back to an integer ID."""
    try:
        return int(hxid, 16)
    except (ValueError, TypeError):
        return None

# 3. ENCRYPTION/DECRYPTION
def encrypt(data: str) -> str:
    """Simple reversible encryption for callback data."""
    try:
        if not data or not isinstance(data, str):
            return ""
        combined = f"{data}|{BOT_TOKEN[-6:]}"
        return base64.urlsafe_b64encode(combined.encode()).decode()
    except Exception as e:
        logging.error(f"Encryption failed: {e}")
        return ""

def decrypt(encrypted_data: str) -> str:
    """Reverses the encryption to get the original data."""
    try:
        if not encrypted_data or not isinstance(encrypted_data, str):
            return ""
        decoded = base64.urlsafe_b64decode(encrypted_data.encode()).decode()
        original, salt = decoded.rsplit("|", 1)
        if salt == BOT_TOKEN[-6:]:
            return original
        return ""
    except Exception as e:
        logging.error(f"Decryption failed: {e}")
        return ""

# 4. INPUT VALIDATION & SANITIZATION
def validate_telegram_id(telegram_id: str) -> bool:
    """Validates that a given string is a plausible Telegram user ID."""
    return isinstance(telegram_id, str) and telegram_id.isdigit() and len(telegram_id) < 15

def sanitize_text(text: str) -> str:
    """Basic text sanitization to remove harmful scripts and limit length."""
    if not text:
        return ""
    sanitized = re.sub(r"<script.*?</script>", "", text, flags=re.IGNORECASE)
    return sanitized[:4096]

# 5. RATE LIMITING
def check_rate_limit(user_id: str, limit: int = 5, window: int = 10) -> bool:
    """Simple in-memory rate limiting to prevent spam."""
    import time
    current_time = time.time()
    if user_id not in rate_limit_storage:
        rate_limit_storage[user_id] = []
    
    rate_limit_storage[user_id] = [t for t in rate_limit_storage[user_id] if current_time - t < window]
    
    if len(rate_limit_storage[user_id]) >= limit:
        return False
    
    rate_limit_storage[user_id].append(current_time)
    return True

# 6. DATABASE OPERATIONS
async def get_user_by_telegram_id(db, telegram_id: str) -> Optional[Dict]:
    """Retrieves a user from the database by their Telegram ID."""
    try:
        if not validate_telegram_id(telegram_id): return None
        result = await db.prepare("SELECT * FROM users WHERE telegram_user_id = ?").bind(telegram_id).first()
        return result.to_py() if result else None
    except Exception as e:
        logging.error(f"DB error getting user {telegram_id}: {e}")
        return None

async def create_user(db, telegram_id: str) -> Optional[Dict]:
    """Creates a new user in the database with default language 'en'."""
    try:
        if not validate_telegram_id(telegram_id): return None
        rkey = rndKey()
        await db.prepare("INSERT INTO users (telegram_user_id, rkey, language) VALUES (?, ?, 'en')") \
                .bind(telegram_id, rkey).run()
        return await get_user_by_telegram_id(db, telegram_id)
    except Exception as e:
        logging.error(f"DB error creating user {telegram_id}: {e}")
        return None

async def update_user_language(db, telegram_id: str, lang_code: str) -> bool:
    """Updates the user's language preference."""
    try:
        await db.prepare("UPDATE users SET language = ? WHERE telegram_user_id = ?") \
                .bind(lang_code, telegram_id).run()
        return True
    except Exception as e:
        logging.error(f"DB error updating language: {e}")
        return False

async def update_user_target(db, telegram_id: str, target_user: str) -> bool:
    """Sets or clears the target user for sending a new message."""
    try:
        await db.prepare("UPDATE users SET target_user = ? WHERE telegram_user_id = ?") \
                .bind(target_user, telegram_id).run()
        return True
    except Exception as e:
        logging.error(f"DB error updating user target: {e}")
        return False

async def check_if_blocked(db, blocker_id: str, blocked_id: str) -> bool:
    """Checks if a user has blocked another."""
    try:
        result = await db.prepare("SELECT 1 FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?") \
                         .bind(blocker_id, blocked_id).first()
        return result is not None
    except Exception as e:
        logging.error(f"DB error checking block status: {e}")
        return False

async def block_user(db, blocker_id: str, blocked_id: str) -> bool:
    """Adds a block record to the database."""
    try:
        await db.prepare("INSERT OR IGNORE INTO blocked_users (blocker_id, blocked_id) VALUES (?, ?)") \
                .bind(blocker_id, blocked_id).run()
        return True
    except Exception as e:
        logging.error(f"DB error blocking user: {e}")
        return False

async def unblock_user(db, blocker_id: str, blocked_id: str) -> bool:
    """Removes a block record from the database."""
    try:
        await db.prepare("DELETE FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?") \
                .bind(blocker_id, blocked_id).run()
        return True
    except Exception as e:
        logging.error(f"DB error unblocking user: {e}")
        return False

async def create_message_mapping(db, original_message_id, original_chat_id, forwarded_message_id, forwarded_chat_id, sender_id, receiver_id):
    """Stores a mapping between an original message and its forwarded/copied version to track replies."""
    try:
        await db.prepare(
            "INSERT INTO message_mappings (original_message_id, original_chat_id, forwarded_message_id, forwarded_chat_id, sender_id, receiver_id) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        ).bind(original_message_id, original_chat_id, forwarded_message_id, forwarded_chat_id, sender_id, receiver_id).run()
        return True
    except Exception as e:
        logging.error(f"DB error creating message mapping: {e}")
        return False

async def get_mapping_by_forwarded_id(db, forwarded_message_id, forwarded_chat_id):
    """Retrieves a message mapping based on the ID of the message that was replied to."""
    try:
        result = await db.prepare(
            "SELECT * FROM message_mappings WHERE forwarded_message_id = ? AND forwarded_chat_id = ?"
        ).bind(str(forwarded_message_id), str(forwarded_chat_id)).first()
        return result.to_py() if result else None
    except Exception as e:
        logging.error(f"DB error getting message mapping: {e}")
        return None

# 7. TELEGRAM API COMMUNICATION
async def postReq(tgMethod: str, payload: Dict) -> Dict:
    """Sends a request to the Telegram Bot API with error handling."""
    try:
        options = {
            "body": json.dumps({k: v for k, v in payload.items() if v is not None}),
            "method": "POST",
            "headers": {"content-type": "application/json;charset=UTF-8"},
        }
        response = await fetch(f"https://api.telegram.org/bot{BOT_TOKEN}/{tgMethod}", to_js(options))
        if not response.ok:
            response_text = await response.text()
            logging.error(f"Telegram API HTTP Error {response.status} for {tgMethod}: {response_text}")
            return {"ok": False, "description": f"HTTP Error: {response.status}"}
        
        body = await response.json()
        result = body.to_py()
        if not result.get("ok", False):
            logging.error(f"Telegram API Error in {tgMethod}: {result.get('description', 'Unknown error')}")
        return result
    except Exception as e:
        logging.error(f"Request failed for {tgMethod}: {e}")
        return {"ok": False, "description": str(e)}

# 8. AUTHORIZATION
def is_user_authorized(user_data: Dict) -> bool:
    """Checks if a user is in the allowed list (if not set to 'ALL')."""
    if str(ALLOWED).lower() == "all":
        return True
    allowed_users = [u.strip() for u in ALLOWED.split(",") if u.strip()]
    return user_data.get("username") in allowed_users

@handler
async def on_fetch(request, env):
    """Main request handler for the Cloudflare Worker."""
    try:
        url = request.url
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        HOOK = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]
        db = env.DB

        if path == "init":
            body = await postReq("setWebhook", {"url": f"{base_url}/{HOOK}", "allowed_updates": ["message", "callback_query"]})
            return Response(json.dumps(body), headers={"Content-Type": "application/json"})
        
        if path == HOOK:
            tgResponse = await request.json()

            # --- MESSAGE HANDLER ---
            if "message" in tgResponse:
                message = tgResponse["message"]
                chatId = str(message["from"]["id"])
                text = sanitize_text(message.get("text", ""))

                if not check_rate_limit(chatId):
                    await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string("en", "RATE_LIMIT")})
                    return Response("rate_limited", status=429)

                if not is_user_authorized(message["from"]):
                    return Response("unauthorized", status=403)
                
                user = await get_user_by_telegram_id(db, chatId)
                if not user:
                    user = await create_user(db, chatId)
                    if not user:
                        await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string("en", "USER_CREATION_ERROR")})
                        return Response("user_creation_failed", status=500)
                
                lang = user.get("language", "en")

                GUIDE_BUTTON = get_lang_string(lang, "GUIDE_BUTTON")
                NEW_LINK_BUTTON = get_lang_string(lang, "NEW_LINK_BUTTON")
                LANG_BUTTON = get_lang_string(lang, "LANG_BUTTON")
                CANCEL_BUTTON = get_lang_string(lang, "CANCEL_BUTTON")

                default_keyboard = {
                    "keyboard": [[{"text": GUIDE_BUTTON}, {"text": NEW_LINK_BUTTON}], [{"text": LANG_BUTTON}]],
                    "resize_keyboard": True
                }

                # --- LOGIC FOR REPLIES ---
                if "reply_to_message" in message:
                    replied_to_msg = message["reply_to_message"]
                    
                    if str(replied_to_msg.get("from", {}).get("id")) == BOT_TELEGRAM_ID:
                        mapping = await get_mapping_by_forwarded_id(db, str(replied_to_msg["message_id"]), chatId)
                        
                        if mapping:
                            original_sender_id = mapping["sender_id"]
                            original_message_id_for_threading = mapping["original_message_id"]

                            if await check_if_blocked(db, original_sender_id, chatId):
                                await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "REPLY_BLOCKED")})
                                return Response("reply_blocked", status=200)

                            receiver = await get_user_by_telegram_id(db, original_sender_id)
                            receiver_lang = receiver.get("language", "en")
                            
                            copied_reply = await postReq("copyMessage", {
                                "chat_id": original_sender_id,
                                "from_chat_id": chatId,
                                "message_id": message["message_id"],
                                "reply_to_message_id": original_message_id_for_threading,
                                "reply_markup": json.dumps({
                                    "inline_keyboard": [[{"text": get_lang_string(receiver_lang, "BLOCK_BUTTON"), "callback_data": f"block_{encrypt(chatId)}"}]]
                                })
                            })

                            if copied_reply.get("ok"):
                                newly_sent_message_id = copied_reply['result']['message_id']
                                await create_message_mapping(db, str(message['message_id']), chatId, str(newly_sent_message_id), original_sender_id, chatId, original_sender_id)
                                await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "REPLY_SENT"), "reply_to_message_id": message["message_id"]})
                            else:
                                await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "REPLY_ERROR"), "reply_to_message_id": message["message_id"]})
                            
                            return Response("reply_processed", status=200)

                # --- LOGIC FOR COMMANDS AND NEW MESSAGES ---
                if text.startswith("/start"):
                    match = re.search(r"/start (\w+)_(\w+)", text)
                    if match:
                        param_rkey, param_id = match.groups()
                        target_id = revHxId(param_id)
                        target_result = await db.prepare("SELECT * FROM users WHERE id = ?").bind(int(target_id)).first() if target_id else None

                        if target_result and target_result.to_py()["rkey"] == param_rkey:
                            targetUser = target_result.to_py()
                            
                            receiver_name = "a user"
                            try:
                                chat_info = await postReq("getChat", {"chat_id": targetUser["telegram_user_id"]})
                                if chat_info.get("ok"):
                                    receiver_name = sanitize_text(chat_info["result"].get("first_name", "a user"))
                            except Exception as e:
                                logging.error(f"Could not fetch receiver name: {e}")

                            await update_user_target(db, chatId, targetUser["telegram_user_id"])
                            
                            cancel_keyboard = {
                                "keyboard": [[{"text": CANCEL_BUTTON}]],
                                "resize_keyboard": True
                            }
                            
                            await postReq("sendMessage", {
                                "chat_id": chatId,
                                "text": get_lang_string(lang, "START_REPLY").format(receiver_name),
                                "reply_markup": json.dumps(cancel_keyboard),
                            })
                        else:
                            await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "INVALID_LINK"), "reply_markup": json.dumps(default_keyboard)})
                    else:
                        await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "WELCOME"), "reply_markup": json.dumps(default_keyboard)})
                    return Response("start_handled", status=200)

                elif text == NEW_LINK_BUTTON:
                    mylink = f"https://t.me/{BOT_ID}?start={user['rkey']}_{hxId(user['id'])}"
                    await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "LINK_GENERATED").format(mylink), "parse_mode": "MarkdownV2"})
                    return Response("link_generated", status=200)

                elif text == GUIDE_BUTTON:
                    await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "GUIDE_TEXT"), "reply_markup": json.dumps(default_keyboard)})
                    return Response("guide_sent", status=200)

                elif text == LANG_BUTTON:
                    new_lang = "en" if lang == "fa" else "fa"
                    await update_user_language(db, chatId, new_lang)
                    
                    new_default_keyboard = {
                        "keyboard": [[
                            {"text": get_lang_string(new_lang, "GUIDE_BUTTON")}, 
                            {"text": get_lang_string(new_lang, "NEW_LINK_BUTTON")}
                        ], [{"text": get_lang_string(new_lang, "LANG_BUTTON")}]],
                        "resize_keyboard": True
                    }
                    await postReq("sendMessage", {
                        "chat_id": chatId,
                        "text": get_lang_string(new_lang, "LANG_SET"),
                        "reply_markup": json.dumps(new_default_keyboard)
                    })
                    return Response("lang_changed", status=200)

                elif text == CANCEL_BUTTON:
                    if user and user.get("target_user"):
                        await update_user_target(db, chatId, "")
                        await postReq("sendMessage", {
                            "chat_id": chatId,
                            "text": get_lang_string(lang, "CANCEL_SUCCESS"),
                            "reply_markup": json.dumps(default_keyboard)
                        })
                    return Response("cancel_success", status=200)

                elif user and user.get("target_user"):
                    target_user_id = user["target_user"]
                    if await check_if_blocked(db, target_user_id, chatId):
                        await update_user_target(db, chatId, "")
                        await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "MESSAGE_BLOCKED"), "reply_markup": json.dumps(default_keyboard)})
                        return Response("blocked_user_message", status=200)

                    receiver = await get_user_by_telegram_id(db, target_user_id)
                    receiver_lang = receiver.get("language", "en")

                    copied_message = await postReq("copyMessage", {
                        "chat_id": target_user_id, 
                        "from_chat_id": chatId, 
                        "message_id": message["message_id"],
                        "reply_markup": json.dumps({
                            "inline_keyboard": [[{"text": get_lang_string(receiver_lang, "BLOCK_BUTTON"), "callback_data": f"block_{encrypt(chatId)}"}]]
                        })
                    })
                    
                    if copied_message.get("ok"):
                        copied_message_id = copied_message["result"]["message_id"]
                        await create_message_mapping(db, str(message["message_id"]), chatId, str(copied_message_id), target_user_id, chatId, target_user_id)
                        await update_user_target(db, chatId, "")
                        await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "MESSAGE_SENT"), "reply_markup": json.dumps(default_keyboard)})
                    else:
                        error_desc = copied_message.get("description", "Unknown error")
                        user_blocked_bot = "bot was blocked" in error_desc.lower() or "user is deactivated" in error_desc.lower()
                        error_text = get_lang_string(lang, "USER_BLOCKED_BOT") if user_blocked_bot else get_lang_string(lang, "SEND_ERROR").format(error_desc)
                        await postReq("sendMessage", {"chat_id": chatId, "text": error_text, "reply_markup": json.dumps(default_keyboard)})
                    return Response("message_sent", status=200)
                
                else:
                    await postReq("sendMessage", {"chat_id": chatId, "text": get_lang_string(lang, "NO_TARGET"), "reply_markup": json.dumps(default_keyboard)})
                    return Response("no_target", status=200)

            # --- CALLBACK QUERY HANDLER ---
            if "callback_query" in tgResponse:
                callback = tgResponse["callback_query"]
                chatId = str(callback["from"]["id"])
                data = callback["data"]
                message_info = callback.get("message", {})
                
                user = await get_user_by_telegram_id(db, chatId)
                lang = user.get("language", "en")

                if data.startswith("block_"):
                    blocked_id = decrypt(data.replace("block_", ""))
                    if blocked_id and await block_user(db, chatId, blocked_id):
                        await postReq("answerCallbackQuery", {"callback_query_id": callback["id"], "text": get_lang_string(lang, "USER_BLOCKED")})
                        await postReq("editMessageReplyMarkup", {
                            "chat_id": chatId, "message_id": message_info.get("message_id"),
                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": get_lang_string(lang, "UNBLOCK_BUTTON"), "callback_data": f"unblock_{encrypt(blocked_id)}"}]]})
                        })
                    else:
                        await postReq("answerCallbackQuery", {"callback_query_id": callback["id"], "text": get_lang_string(lang, "BLOCK_ERROR"), "show_alert": True})

                elif data.startswith("unblock_"):
                    unblocked_id = decrypt(data.replace("unblock_", ""))
                    if unblocked_id and await unblock_user(db, chatId, unblocked_id):
                        await postReq("answerCallbackQuery", {"callback_query_id": callback["id"], "text": get_lang_string(lang, "USER_UNBLOCKED")})
                        await postReq("editMessageReplyMarkup", {
                            "chat_id": chatId, "message_id": message_info.get("message_id"),
                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": get_lang_string(lang, "BLOCK_BUTTON"), "callback_data": f"block_{encrypt(unblocked_id)}"}]]})
                        })
                    else:
                        await postReq("answerCallbackQuery", {"callback_query_id": callback["id"], "text": get_lang_string(lang, "UNBLOCK_ERROR"), "show_alert": True})
                
                return Response("callback_processed", status=200)

        return Response("ok", status=200)

    except Exception as e:
        import traceback
        logging.error(f"❌ Unhandled Exception: {e}\n{traceback.format_exc()}")
        return Response(json.dumps({"error": "Internal Server Error"}), status=500, headers={"Content-Type": "application/json"})
