# memory/client.py — HTTP client for the Xeon memory API.
#
# All functions are non-fatal: return empty/false result on any error
# so a Xeon outage never crashes the brain.
#
# Endpoints (jarvis-memory service on Xeon :8083):
#   POST /knowledge/add    {text, title}
#   POST /knowledge/search {query, n}
#   POST /episodes/add     {text, timestamp}
#   POST /episodes/search  {query, n}

import httpx
from config import MEMORY_URL

_TIMEOUT = 5


def add_knowledge(text: str, title: str = "") -> dict:
    try:
        resp = httpx.post(
            f"{MEMORY_URL}/knowledge/add",
            json={"text": text, "title": title},
            timeout=_TIMEOUT,
        )
        return resp.json()
    except Exception:
        return {"success": False}


def search_knowledge(query: str, n: int = 3) -> list[dict]:
    try:
        resp = httpx.post(
            f"{MEMORY_URL}/knowledge/search",
            json={"query": query, "n": n},
            timeout=_TIMEOUT,
        )
        return resp.json().get("results", [])
    except Exception:
        return []


def add_episode(text: str, timestamp: str = "") -> dict:
    try:
        resp = httpx.post(
            f"{MEMORY_URL}/episodes/add",
            json={"text": text, "timestamp": timestamp},
            timeout=_TIMEOUT,
        )
        return resp.json()
    except Exception:
        return {"success": False}


def search_episodes(query: str, n: int = 5) -> list[dict]:
    try:
        resp = httpx.post(
            f"{MEMORY_URL}/episodes/search",
            json={"query": query, "n": n},
            timeout=_TIMEOUT,
        )
        return resp.json().get("results", [])
    except Exception:
        return []
