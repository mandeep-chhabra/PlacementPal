import os
import json
import time
import logging
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
import base64

from bs4 import BeautifulSoup
import dateparser
from dateparser.search import search_dates

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- CONFIG ----------------
TELEGRAM_BOT_TOKEN = "8251363454:AAH07yQ80vZljGB3HR3LwITAxmY5k6KPnW0"
CHAT_ID = "1228212476"  # Replace with your chat id
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
PROCESSED_FILE = "processed_ids.json"
PENDING_FILE = "pending_events.json"

# Gmail query - adjust keywords as you want
GMAIL_QUERY = 'placement OR interview OR recruitment newer_than:14d'
MAX_FETCH = 10   # max messages to retrieve per fetch

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------- Helpers for persistence ----------------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

processed_ids = load_json(PROCESSED_FILE, [])
pending_events = load_json(PENDING_FILE, {})

# ---------------- Google Auth (persist token.json) ----------------
def load_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # persist token (json string) so you don't re-authorize next run
        with open(TOKEN_FILE, "w", encoding="utf-8") as t:
            t.write(creds.to_json())
    return creds

def get_gmail_service():
    creds = load_creds()
    return build("gmail", "v1", credentials=creds)

def get_calendar_service():
    creds = load_creds()
    return build("calendar", "v3", credentials=creds)

# ---------------- Email parsing ----------------
def _decode_base64url(data):
    if not data:
        return ""
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode(errors="ignore")

def extract_message_text(payload):
    """
    Walk payload and extract text/plain if available, otherwise html -> text
    """
    if payload is None:
        return ""
    mime = payload.get("mimeType", "")
    if mime == "text/plain" and payload.get("body", {}).get("data"):
        return _decode_base64url(payload["body"]["data"])
    if mime == "text/html" and payload.get("body", {}).get("data"):
        html = _decode_base64url(payload["body"]["data"])
        return BeautifulSoup(html, "html.parser").get_text(separator="\n")
    # parts
    parts = payload.get("parts", [])
    text_chunks = []
    for part in parts:
        text_chunks.append(extract_message_text(part))
    return "\n".join([t for t in text_chunks if t])

def parse_datetime_from_text(text):
    """
    Try to extract candidate datetimes from text with dateparser.search.search_dates.
    Prioritize future dates; return a timezone-aware datetime in Asia/Kolkata or None.
    """
    if not text or len(text.strip()) < 5:
        return None
    try:
        results = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": False,
                # stricter parsing sometimes misses friendly phrases; omit STRICT_PARSING
            },
        )
    except Exception as e:
        LOG.debug("search_dates failed: %s", e)
        results = None

    if not results:
        return None

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    candidates = []
    for snippet, dt in results:
        if not isinstance(dt, datetime):
            continue
        # if parsed dt has no time (midnight), we still accept it
        # make dt timezone-aware in Asia/Kolkata
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        # if dt is in past but within 12 hours tolerance, still accept as todays/time
        if dt >= now - timedelta(hours=1):
            candidates.append(dt)
    if not candidates:
        # fallback: pick first parsed but ensure tz
        dt = results[0][1]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return dt
    # return the earliest candidate in future (closest upcoming)
    candidates.sort()
    return candidates[0]

# ---------------- Gmail fetching ----------------
def fetch_unprocessed_messages():
    """
    Fetch messages matching GMAIL_QUERY, filter out already processed IDs,
    return list of message dicts with id, subject, sender, snippet, parsed_datetime
    """
    service = get_gmail_service()
    LOG.info("Fetching messages with query: %s", GMAIL_QUERY)
    response = service.users().messages().list(userId="me", q=GMAIL_QUERY, maxResults=MAX_FETCH).execute()
    msgs = response.get("messages", [])
    results = []
    for m in msgs:
        mid = m["id"]
        if mid in processed_ids or mid in pending_events:
            continue
        msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(no subject)")
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "(unknown)")
        body_text = extract_message_text(msg.get("payload", {}))
        snippet = msg.get("snippet", "") or (body_text[:200] + "...")

        # try parse datetime from subject + body
        combined = f"{subject}\n\n{body_text}"
        parsed_dt = parse_datetime_from_text(combined)

        results.append({
            "id": mid,
            "subject": subject,
            "sender": sender,
            "snippet": snippet,
            "body_text": body_text,
            "parsed_dt": parsed_dt.isoformat() if parsed_dt else None
        })
    return results

# ---------------- Telegram handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start - welcome + auto-detect chat id if not provided, and fetch new messages
    """
    global CHAT_ID
    user_chat_id = str(update.effective_chat.id)
    LOG.info("/start from chat %s", user_chat_id)
    if not CHAT_ID:
        CHAT_ID = user_chat_id
        await update.message.reply_text("Chat ID captured. I will send notifications to this chat.")
    else:
        await update.message.reply_text("Hi — fetching new placement mails now...")

    # after acknowledging, run fetch and send notices
    await fetch_and_send(context)

async def fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual /fetch command to force a fetch"""
    await update.message.reply_text("Fetching placement mails...")
    await fetch_and_send(context)

async def fetch_and_send(context: ContextTypes.DEFAULT_TYPE):
    """
    Fetch unprocessed Gmail messages, save to pending_events, and send Telegram message with buttons.
    """
    service = context.application  # not used directly - placeholder
    new_msgs = fetch_unprocessed_messages()
    if not new_msgs:
        # No mails found
        if CHAT_ID:
            await context.bot.send_message(chat_id=CHAT_ID, text="No new placement-related emails found.")
        return

    for msg in new_msgs:
        # unique short id for callback (timestamp + short)
        short_id = str(int(time.time()*1000))[-10:]
        pending_events[short_id] = {
            "gmail_id": msg["id"],
            "subject": msg["subject"],
            "sender": msg["sender"],
            "snippet": msg["snippet"],
            "body_text": msg["body_text"],
            "parsed_dt": msg["parsed_dt"]
        }
        save_json(PENDING_FILE, pending_events)

        # build message text
        parsed_dt = msg["parsed_dt"]
        dt_readable = parsed_dt if parsed_dt else "No date/time detected"
        text = f"📧 *{msg['subject']}*\nFrom: {msg['sender']}\n\n_{msg['snippet']}_\n\n*Detected time:* {dt_readable}\n\nTap ✅ to add to Google Calendar."
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve|{short_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject|{short_id}"),
                ]
            ]
        )
        if CHAT_ID:
            await context.bot.send_message(chat_id=CHAT_ID, text=text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            LOG.warning("CHAT_ID not set; cannot send message to Telegram. Use /start in a chat to capture it.")

# callback handler for approve/reject
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = data.split("|")
    if len(parts) != 2:
        await query.edit_message_text("Invalid callback data.")
        return
    action, short_id = parts
    event = pending_events.get(short_id)
    if not event:
        await query.edit_message_text("This item expired or was already processed.")
        return

    if action == "reject":
        # mark as processed (so it won't reappear)
        processed_ids.append(event["gmail_id"])
        save_json(PROCESSED_FILE, processed_ids)
        del pending_events[short_id]
        save_json(PENDING_FILE, pending_events)
        await query.edit_message_text(f"❌ Rejected: {event['subject']}")
        return

    # APPROVE: create calendar event at parsed datetime (or ask user if none)
    parsed_iso = event.get("parsed_dt")
    if not parsed_iso:
        await query.edit_message_text("No date/time detected in the email. Please reply with a date/time or reject.")
        return

    try:
        start_dt = datetime.fromisoformat(parsed_iso)
        # ensure tz-aware Asia/Kolkata
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    except Exception as e:
        LOG.exception("Failed to parse stored datetime: %s", e)
        await query.edit_message_text("Failed to interpret the detected date/time. Please reject or set manually.")
        return

    # default event duration = 1 hour
    end_dt = start_dt + timedelta(hours=1)

    # create calendar event
    cal = get_calendar_service()
    event_body = {
        "summary": event["subject"],
        "description": f"From: {event['sender']}\n\n{event['body_text'][:1000]}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60 * 24},  # 1 day before via email
            ],
        },
    }
    created = cal.events().insert(calendarId="primary", body=event_body).execute()

    # mark as processed, remove from pending
    processed_ids.append(event["gmail_id"])
    save_json(PROCESSED_FILE, processed_ids)
    del pending_events[short_id]
    save_json(PENDING_FILE, pending_events)

    await query.edit_message_text(f"✅ Added to calendar: {event['subject']}\n{created.get('htmlLink')}")

# ---------------- main ----------------
def main():
    # sanity checks
    if not os.path.exists(CREDENTIALS_FILE):
        LOG.error("Missing %s. Create OAuth credentials in Google Cloud Console and save as %s", CREDENTIALS_FILE, CREDENTIALS_FILE)
        return
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("YOUR_"):
        LOG.error("Set TELEGRAM_BOT_TOKEN at the top of the script.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fetch", fetch_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    LOG.info("Bot started. Use /start in the chat you want notifications to be sent to, then /fetch to fetch emails.")
    app.run_polling()

if __name__ == "__main__":
    main()
