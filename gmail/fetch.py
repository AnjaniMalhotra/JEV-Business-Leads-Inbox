"""Read emails from Gmail over IMAP and turn them into the app's email format. Read-only: nothing is marked as read."""
import base64
import email
import re
from datetime import datetime, timezone
from email import policy
from email.utils import parseaddr, parsedate_to_datetime

from triage.text import clean_body

MAX_BODY_CHARS = 20_000
MAX_ATTACHMENT_BYTES = 5_000_000  # bigger files are listed but not downloaded
_STYLE_SCRIPT = re.compile(r"(?is)<(style|script)\b.*?</\1>")
_GM_IDS = re.compile(rb"X-GM-MSGID (\d+) X-GM-THRID (\d+)")


def fetch(conn, query: str, limit: int) -> list[dict]:
    """The newest `limit` inbox emails matching a Gmail search (e.g. "newer_than:7d")."""
    conn.select("INBOX", readonly=True)  # read-only mailbox: no flags change
    _, data = conn.uid("SEARCH", "X-GM-RAW", '"' + query.replace('"', "'") + '"')  # Gmail's own search syntax
    uids = data[0].split()[-limit:]
    emails = []
    for uid in reversed(uids):  # newest first
        _, parts = conn.uid("FETCH", uid, "(X-GM-MSGID X-GM-THRID BODY.PEEK[])")  # PEEK: stays unread
        head, raw = parts[0][0], parts[0][1]
        ids = _GM_IDS.search(head)
        emails.append(parse(raw, ids.group(1).decode() if ids else uid.decode(), int(ids.group(2)) if ids else 0))
    return emails


def parse(raw: bytes, msg_id: str, thread_id: int) -> dict:
    """A raw email -> the app's email dict (plain text for Jev, HTML for display, attachments)."""
    msg = email.message_from_bytes(raw, policy=policy.default)
    plain, html, files = [], [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_filename():  # an attachment
            data = part.get_payload(decode=True) or b""
            files.append({"name": part.get_filename(), "mime": part.get_content_type(), "size": len(data)}
                         | ({"data": base64.b64encode(data).decode()} if len(data) <= MAX_ATTACHMENT_BYTES else {}))
        elif part.get_content_type() in ("text/plain", "text/html"):
            (plain if part.get_content_type() == "text/plain" else html).append(part.get_content())
    body_html = _STYLE_SCRIPT.sub(" ", "\n".join(html)) if html else None
    text = "\n".join(plain).strip() or clean_body(body_html or "", MAX_BODY_CHARS)
    try:
        received = parsedate_to_datetime(msg["date"]).astimezone(timezone.utc)
    except (TypeError, ValueError):
        received = datetime.now(timezone.utc)
    tags = (["auto-submitted"] if (msg["auto-submitted"] or "no").lower() != "no" else []) \
        + (["bulk"] if msg["list-unsubscribe"] else [])  # Header hints used by the free rules
    return {
        "gmail_id": msg_id, "thread_id": format(thread_id, "x") if thread_id else None, "message_id": msg["message-id"],
        "sender": parseaddr(str(msg["from"] or ""))[1] or "unknown",
        "recipient": parseaddr(str(msg["to"] or ""))[1] or "me",
        "subject": str(msg["subject"] or "(no subject)"),
        "body": text[:MAX_BODY_CHARS], "html": body_html,
        "received_at": received.isoformat(timespec="minutes"), "tags": tags, "attachments": files,
    }
