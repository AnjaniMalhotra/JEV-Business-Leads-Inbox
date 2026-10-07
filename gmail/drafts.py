"""Save an LLM reply as a draft in the visitor's Gmail Drafts, in the original thread. Nothing is ever sent."""
import html
import imaplib
import re
import time
from datetime import datetime
from email.message import EmailMessage

DRAFTS_URL = "https://mail.google.com/mail/u/0/#drafts"


def drafts_folder(conn) -> str:
    """Gmail's Drafts folder (its name depends on the account's language, so look for the \\Drafts flag)."""
    _, folders = conn.list()
    for line in folders or []:
        text = line.decode(errors="replace")
        if "\\Drafts" in text:
            return re.search(r'"([^"]+)"\s*$', text).group(1)
    return "[Gmail]/Drafts"


def as_html(text: str) -> str:
    """Plain text -> simple HTML: blank lines start a paragraph, single line breaks stay line breaks."""
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def save_reply_draft(conn, email: dict, text: str, from_address: str) -> str:
    """Add the reply to Drafts. Returns when it was saved (each save adds a draft; nothing is overwritten)."""
    msg = EmailMessage()  # Build a plain reply email
    msg["From"], msg["To"] = from_address, email["sender"]
    subject = email["subject"]
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    if isinstance(email.get("message_id"), str) and email["message_id"]:  # Gmail threads it with the original
        msg["In-Reply-To"] = msg["References"] = email["message_id"]
    msg.set_content(text)  # plain text for simple mail apps
    msg.add_alternative(as_html(text), subtype="html")  # Gmail opens the draft as rich text, so lines flow to the page width
    conn.append(f'"{drafts_folder(conn)}"', "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    return datetime.now().strftime("%H:%M")
