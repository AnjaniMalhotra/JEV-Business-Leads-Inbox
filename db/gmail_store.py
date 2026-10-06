"""Gmail-specific storage: emails loaded from Gmail (one row per Gmail message) and reply-draft links."""
import json

from db.store import connect, reset_emails


def upsert_gmail_emails(emails: list[dict]) -> int:
    """Add new emails; refresh display details of ones already stored (Jev's results are kept). Returns how many were new."""
    with connect() as conn:
        # Gmail ids we already have
        known = {row[0] for row in conn.execute("SELECT gmail_id FROM emails WHERE gmail_id IS NOT NULL")}
        conn.executemany(
            """INSERT INTO emails (gmail_id, thread_id, message_id, sender, recipient, subject, body, html,
               received_at, tags, attachments)
               VALUES (:gmail_id, :thread_id, :message_id, :sender, :recipient, :subject, :body, :html,
               :received_at, :tags, :attachments)
               ON CONFLICT(gmail_id) DO UPDATE SET thread_id = excluded.thread_id, message_id = excluded.message_id,
               recipient = excluded.recipient, html = excluded.html, attachments = excluded.attachments""",
            [{**e, "tags": ",".join(e["tags"]), "attachments": json.dumps(e["attachments"])} for e in emails],
        )
    return sum(e["gmail_id"] not in known for e in emails)


def set_gmail_draft(email_id: int, draft_id: str) -> None:  # Which Gmail draft belongs to this email
    with connect() as conn:
        conn.execute("UPDATE drafts SET gmail_draft_id = ? WHERE email_id = ?", (draft_id, email_id))


def clear_emails() -> None:
    """Remove every email and everything derived from it from the app (Gmail itself is never touched)."""
    reset_emails([])
