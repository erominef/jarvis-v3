# tools/notify.py — Proactive Telegram notification to owner.
#
# One-way only — sends messages and files to TELEGRAM_OWNER_ID.
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


def telegram_send_file(path: str, caption: str = "") -> str:
    """Send a workspace file to the owner as a Telegram document attachment."""
    from pathlib import Path
    _WORKSPACE = (Path(__file__).parent.parent / "workspace").resolve()

    clean = path.strip().lstrip("/")
    if clean.startswith("workspace/"):
        clean = clean[len("workspace/"):]
    file_path = (_WORKSPACE / clean).resolve()
    try:
        file_path.relative_to(_WORKSPACE)
    except ValueError:
        return "Rejected: path is outside workspace/."
    if not file_path.exists():
        return f"File not found: workspace/{clean}"
    if not file_path.is_file():
        return f"Not a file: workspace/{clean}"

    if not TELEGRAM_BOT_TOKEN:
        return "Telegram not configured — TELEGRAM_BOT_TOKEN missing."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                url,
                data={"chat_id": TELEGRAM_OWNER_ID, "caption": caption},
                files={"document": (file_path.name, f)},
                timeout=30.0,
            )
        r.raise_for_status()
        return f"File sent: {file_path.name} ({file_path.stat().st_size // 1024} KB)"
    except httpx.HTTPStatusError as e:
        return f"Telegram error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"File send failed: {e}"
