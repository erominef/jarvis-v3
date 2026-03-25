# memory/episodes.py — Episodic memory: record and retrieve past conversations.
#
# record_episode(user_text, assistant_reply)
#   Condenses the exchange into a summary and stores it on Xeon.
#   Called after every conversation turn. Non-fatal.
#
# retrieve_context(user_input, n=5) -> str
#   Semantic search over all stored episodes.
#   Returns formatted "## Relevant Past Context" block, or "" if empty/unavailable.

from datetime import datetime, timezone
from memory import client


def record_episode(user_text: str, assistant_reply: str) -> None:
    summary = f"User: {user_text[:200]} | Jarvis: {assistant_reply[:300]}"
    ts = datetime.now(timezone.utc).isoformat()
    client.add_episode(summary, timestamp=ts)


def retrieve_context(user_input: str, n: int = 5) -> str:
    results = client.search_episodes(user_input, n=n)
    if not results:
        return ""
    lines = ["## Relevant Past Context"]
    for r in results:
        ts = r.get("timestamp", "")[:16].replace("T", " ")
        lines.append(f"[{ts}] {r['text']}")
    return "\n".join(lines)
