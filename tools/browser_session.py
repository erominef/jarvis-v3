# tools/browser_session.py — Interactive browser session tools.
#
# Stateful multi-step browser automation via the browser-session service on Xeon (port 8086).
# Each session persists across calls — open, interact, close.
#
# Workflow: browser_open -> browser_state -> browser_click/browser_type -> browser_close
# Call browser_state after every interaction to get fresh element refs.
#
# Env: BROWSER_SESSION_URL (default: http://100.101.127.60:8086)

import os
import httpx

_TIMEOUT = 30.0


def _url() -> str:
    return os.getenv("BROWSER_SESSION_URL", "http://100.101.127.60:8086").rstrip("/")


def browser_open(url: str) -> dict:
    try:
        r = httpx.post(f"{_url()}/open", json={"url": url}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_open failed: {e}"}


def browser_state(session_id: str) -> dict:
    try:
        r = httpx.get(f"{_url()}/state", params={"session_id": session_id}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_state failed: {e}"}


def browser_click(session_id: str, ref: int) -> dict:
    try:
        r = httpx.post(f"{_url()}/click", json={"session_id": session_id, "ref": ref}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_click failed: {e}"}


def browser_type(session_id: str, ref: int, text: str) -> dict:
    try:
        r = httpx.post(f"{_url()}/type", json={"session_id": session_id, "ref": ref, "text": text}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_type failed: {e}"}


def browser_navigate(session_id: str, url: str) -> dict:
    try:
        r = httpx.post(f"{_url()}/navigate", json={"session_id": session_id, "url": url}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_navigate failed: {e}"}


def browser_close(session_id: str) -> dict:
    try:
        r = httpx.post(f"{_url()}/close", json={"session_id": session_id}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Service unavailable: browser-session not running at {_url()}"}
    except Exception as e:
        return {"error": f"browser_close failed: {e}"}
