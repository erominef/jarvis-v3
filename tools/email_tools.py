# tools/email_tools.py — Email send and read via Xeon email service.
#
# Delegates to the email microservice on Xeon (see xeon-services/email/).
# SMTP credentials are set on the Xeon service via env vars — not passed here.
#
# Env: EMAIL_URL (defaults to Xeon service address)


def email_send(to: str, subject: str, body: str) -> str:
    """Send an email via SMTP. Credentials are configured on the Xeon service."""
    # Implementation omitted.
    raise NotImplementedError


def email_read(folder: str = "INBOX", limit: int = 10, unread_only: bool = True) -> str:
    """
    Read emails via IMAP. Returns list of messages with from/subject/date/snippet.
    folder: mailbox folder name (default INBOX)
    limit: max messages to return (capped at 25)
    unread_only: filter to unseen messages only
    """
    # Implementation omitted.
    raise NotImplementedError
