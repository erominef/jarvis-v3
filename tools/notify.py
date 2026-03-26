# tools/notify.py — Proactive Telegram notification to owner.
#
# One-way only — sends a message to TELEGRAM_OWNER_ID.
# Uses Bot API directly. Does not read messages.

import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID

_TIMEOUT = 10.0


def telegram_notify(message: str) -> str:
    if not TELEGRAM_BOT_TOKEN:
        return "Telegram not configured — TELEGRAM_BOT_TOKEN missing."
    if not message.strip():
        return "Error: message must not be empty."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(
            url,
            json={"chat_id": TELEGRAM_OWNER_ID, "text": message, "parse_mode": "Markdown"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return f"Notification sent ({len(message)} chars)."
    except httpx.HTTPStatusError as e:
        return f"Telegram error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Telegram notify failed: {e}"
