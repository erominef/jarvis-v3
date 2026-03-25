# tools/notify.py — Proactive Telegram notification to owner.
#
# One-way only — sends a message to TELEGRAM_OWNER_ID.
# Uses the Bot API sendMessage endpoint directly (not python-telegram-bot).
# Non-fatal: returns error string on failure, never raises.
#
# Env: TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID


def telegram_notify(message: str) -> str:
    """
    Send a proactive message to the owner via Telegram Bot API.
    Use for status updates, completed task alerts, or observations.
    """
    raise NotImplementedError
