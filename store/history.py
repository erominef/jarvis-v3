# store/history.py — Per-chat conversation history (short-term context).
#
# Stored as JSON at workspace/history/{chat_id}.json.
# Only user and assistant messages are kept — tool/system messages are stripped.
# Capped at 40 messages (20 exchanges) to keep context window manageable.
#
# load_history(chat_id) -> list[dict]
# save_history(chat_id, messages) -> None
# clear_history(chat_id) -> bool   (True if file existed)

import json
from pathlib import Path

_HISTORY_DIR = Path(__file__).parent.parent / "workspace" / "history"
_MAX_MESSAGES = 40  # 20 user + 20 assistant


def _path(chat_id: int) -> Path:
    return _HISTORY_DIR / f"{chat_id}.json"


def load_history(chat_id: int) -> list[dict]:
    p = _path(chat_id)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def save_history(chat_id: int, messages: list[dict]) -> None:
    # Keep only user and assistant messages with non-empty content
    filtered = [
        m for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
    ]
    # Cap at max messages (most recent)
    filtered = filtered[-_MAX_MESSAGES:]
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _path(chat_id).write_text(json.dumps(filtered))


def clear_history(chat_id: int) -> bool:
    p = _path(chat_id)
    if p.exists():
        p.unlink()
        return True
    return False
