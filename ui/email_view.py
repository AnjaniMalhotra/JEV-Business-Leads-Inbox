"""The email pop-up: the email itself, what Jev decided, and a reply."""
import base64
import html

import streamlit as st

from db import store
from gmail.client import thread_url
from ui.data import all_emails
from ui.email_decision import show_decision
from ui.email_reply import show_reply
from ui.labels import PRIORITY, tags, when
from ui.safe_html import email_document, remote_images


# File types that could run code
RISKY = (".exe", ".scr", ".bat", ".cmd", ".js", ".vbs", ".jar", ".msi", ".html", ".htm", ".iso", ".zip")


def badges(row) -> str:
    """Priority and label chips for the pop-up header."""
    if not row["sorted"]:
        return ":violet-badge[Not sorted yet]"
    name, colour = PRIORITY[row["bucket"]]
    return " ".join([f":{colour}-badge[{name}]"] + [f":{c}-badge[{t}]" for t, c in tags(row)])


def show_body(row) -> None:
    body_html = row["html"] if isinstance(row["html"], str) and row["html"].strip() else None
    blocked = remote_images(body_html)  # Remote images can track opens
    show = blocked and st.toggle(f"Show images ({blocked} blocked for privacy)", key=f"img_{row['id']}")
    doc = email_document(body_html, row["body"], bool(show))
    lines = len(row["body"]) / 85 + row["body"].count("\n") + 2
    height = 520 if body_html else int(min(max(lines * 25 + 50, 140), 520))
    # Sandboxed frame: the email can't touch the app
    st.iframe("data:text/html;charset=utf-8;base64," + base64.b64encode(doc.encode()).decode(), height=height)


def file_bytes(row, f: dict) -> bytes:
    """Attachments are stored with the email (files over 5 MB are listed only; open them in Gmail)."""
    return base64.b64decode(f["data"]) if "data" in f else b""


def show_attachments(row) -> None:
    files = store.parse_json(row["attachments"], [])
    if not files:
        return
    st.markdown(f"**Attachments ({len(files)})** :gray[· Jev reads the text only; attachments aren't sent to any AI]")
    for i, f in enumerate(files):
        risky = f["name"].lower().endswith(RISKY)  # Risky files can't be downloaded
        data = file_bytes(row, f) if not risky else b""
        name, button = st.columns([5, 1.2], vertical_alignment="center")
        name.markdown(f"{'⚠ ' if risky else ''}**{f['name']}** :gray[{f['mime']} · {f['size'] / 1024:.1f} KB]"
                      + ("  \n:red[Download blocked: this file type can run code.]" if risky else ""))
        if not risky and data:
            button.download_button("Download", data, f["name"], f["mime"], key=f"dl_{row['id']}_{i}", width="stretch")
        if f["mime"].startswith("image") and data:
            st.image(data, width=300)


def show(email_id: int) -> None:
    row = all_emails().set_index("id").loc[email_id].copy()
    row["id"] = email_id
    st.html(f"<div style='font-size:1.3rem;font-weight:600;margin-bottom:-0.5rem'>{html.escape(row['subject'])}</div>")
    st.markdown(f"**{row['name']}** :gray[&lt;{row['sender']}&gt; · to {row['recipient'] or 'me'} · "
                f"{when(row['received_at'])}]"
                + (f" · [Open in Gmail]({thread_url(row['thread_id'])})" if isinstance(row["thread_id"], str) else "")
                + f"  \n{badges(row)}")
    tab_mail, tab_jev, tab_reply = st.tabs(["Message", "Analysis", "Reply"])  # Message, Analysis, Reply
    with tab_mail:
        show_body(row)
        show_attachments(row)
    with tab_jev:
        show_decision(row)
    with tab_reply:
        show_reply(row)


def _closed() -> None:  # Closing the pop-up clears the list selection
    st.session_state.list_version = st.session_state.get("list_version", 0) + 1  # clears the list selection


@st.dialog("Email", width="large", on_dismiss=_closed)  # The email opens as a large pop-up
def open_email(email_id: int) -> None:
    show(email_id)
