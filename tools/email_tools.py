# tools/email_tools.py — Email send and read via Xeon email service (port 8085).

import os
import httpx

_TIMEOUT = 15.0


def _email_url() -> str:
    return os.getenv("EMAIL_URL", "http://100.101.127.60:8085").rstrip("/")


def email_send(to: str, subject: str, body: str) -> str:
    url = _email_url()
    if not to.strip():
        return "Error: 'to' is required."
    if not subject.strip():
        return "Error: 'subject' is required."
    try:
        r = httpx.post(f"{url}/send", json={"to": to, "subject": subject, "body": body}, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return f"Email send failed: {data.get('error', 'unknown')}"
        return f"Email sent to {to} — '{subject}'"
    except httpx.ConnectError:
        return f"Service unavailable: email service not running at {url}"
    except Exception as e:
        return f"email_send error: {e}"


def email_read(folder: str = "INBOX", limit: int = 10, unread_only: bool = True) -> str:
    url = _email_url()
    try:
        r = httpx.post(
            f"{url}/read",
            json={"folder": folder, "limit": min(limit, 25), "unread_only": unread_only},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return f"Email read failed: {data.get('error', 'unknown')}"
        messages = data.get("messages", [])
        if not messages:
            label = "unread " if unread_only else ""
            return f"No {label}messages in {folder}."
        lines = [f"Inbox — {len(messages)} message(s):"]
        for msg in messages:
            from_ = msg.get("from", "?")
            subject = msg.get("subject", "(no subject)")
            date = msg.get("date", "")
            snippet = msg.get("snippet", "")[:100]
            entry = f"• [{date}] From: {from_}\n  Subject: {subject}"
            if snippet:
                entry += f"\n  {snippet}"
            lines.append(entry)
        return "\n\n".join(lines)
    except httpx.ConnectError:
        return f"Service unavailable: email service not running at {url}"
    except Exception as e:
        return f"email_read error: {e}"
