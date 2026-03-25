# main.py — Email send/receive service for jarvis-v3.
#
# Runs on Xeon in Docker. Wraps smtplib + imaplib with FastAPI.
# Credentials loaded from environment variables (set in docker-compose or .env).
#
# Endpoints:
#   POST /send  {to, subject, body}                          -> {success, error?}
#   POST /read  {folder="INBOX", limit=10, unread_only=True} -> {success, messages, error?}
#   GET  /health                                             -> {status}

import email as _email
import imaplib
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="jarvis-email")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")


class SendRequest(BaseModel):
    to: str
    subject: str
    body: str


class ReadRequest(BaseModel):
    folder: str = "INBOX"
    limit: int = 10
    unread_only: bool = True


@app.post("/send")
def send_email(req: SendRequest):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return {"success": False, "error": "SMTP not configured — set SMTP_HOST, SMTP_USER, SMTP_PASS"}

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = req.to
        msg["Subject"] = req.subject
        msg.attach(MIMEText(req.body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, req.to, msg.as_string())

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/read")
def read_email(req: ReadRequest):
    if not IMAP_HOST or not IMAP_USER or not IMAP_PASS:
        return {"success": False, "error": "IMAP not configured — set IMAP_HOST, IMAP_USER, IMAP_PASS"}

    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, timeout=15) as mail:
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select(req.folder)

            criteria = "UNSEEN" if req.unread_only else "ALL"
            _, data = mail.search(None, criteria)
            ids = data[0].split()

            # Take most recent `limit` messages
            ids = ids[-req.limit:][::-1]

            messages = []
            for uid in ids:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = _email.message_from_bytes(raw)

                from_ = msg.get("From", "")
                subject = msg.get("Subject", "")
                date = msg.get("Date", "")

                # Extract plain text body
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_text = payload.decode("utf-8", errors="replace")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")

                messages.append({
                    "from": from_,
                    "subject": subject,
                    "date": date,
                    "snippet": body_text.strip()[:200],
                })

        return {"success": True, "messages": messages}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/health")
def health():
    smtp_ok = bool(SMTP_HOST and SMTP_USER and SMTP_PASS)
    imap_ok = bool(IMAP_HOST and IMAP_USER and IMAP_PASS)
    return {"status": "ok", "smtp_configured": smtp_ok, "imap_configured": imap_ok}
