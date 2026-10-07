"""The Reply tab: an LLM draft in the chosen tone, editable and copyable. Never sent automatically."""
from urllib.parse import quote

import streamlit as st

from db import feedback, gmail_store
from gmail.drafts import DRAFTS_URL, save_reply_draft
from triage.reply import TONES, draft_reply, reply_error
from ui.gmail_ui import login, open_connection
from ui.sidebar import keys


def show_reply(row) -> None:
    email_id, k = int(row["id"]), keys()
    email = {"id": email_id, "sender": row["sender"], "subject": row["subject"], "body": row["body"]}
    draft = feedback.get_draft(email_id)  # Existing draft, if any
    tone_col, write_col = st.columns([3, 1.2], vertical_alignment="bottom")
    tone = tone_col.segmented_control("Tone", list(TONES), default="Friendly", key=f"tone_{email_id}") or "Friendly"
    if write_col.button("Rewrite" if draft else "Draft reply", type="secondary" if draft else "primary",
                        icon=":material/edit_note:", key=f"write_{email_id}", width="stretch"):
        try:
            with st.spinner(f"{k.get('name', 'The LLM')} is writing…"):
                feedback.save_draft(email_id, draft_reply(email, k, tone), "draft", k.get("name") if k.get("llm_key") else "demo")
            st.rerun()  # only on success: a rerun would wipe the error message below
        except Exception as exc:  # bad key, wrong model name, rate limit, empty reply…
            st.error(reply_error(exc, k.get("name") or "The LLM"), icon=":material/error:")
    if not k.get("llm_key"):  # no key for the chosen provider: drafts are demo text
        st.caption(f"No {k.get('provider') or 'LLM'} key in the sidebar, so drafts are demo text. "
                   "Add the key in the box that matches *Replies are written by*.")
    if not draft:
        if row["sorted"] and row["needs_reply"] < 0.5:
            st.caption("Jev doesn't think this email needs a reply, but you can still draft one.")
        return

    # Editable draft
    text = st.text_area("Reply", draft["text"], height=200, key=f"draft_{email_id}_{draft['created_at']}",
                        label_visibility="collapsed")
    save, copy, gmail = st.columns(3)
    if save.button("Save", icon=":material/save:", width="stretch", key=f"save_{email_id}"):
        feedback.save_draft(email_id, text, "edited", draft["model"])
        st.toast("Draft saved in the app")
    with copy.popover("Copy", icon=":material/content_copy:", width="stretch"):
        st.code(text, language=None, wrap_lines=True)
    if isinstance(row["gmail_id"], str):  # Real Gmail email: save as a threaded draft
        label = "Save another draft" if draft["gmail_draft_id"] else "Save to Gmail drafts"
        if gmail.button(label, type="primary", icon=":material/drafts:", width="stretch", key=f"gdraft_{email_id}",
                        disabled=not login(), help=None if login() else "Connect your Gmail first"):
            try:
                feedback.save_draft(email_id, text, "edited", draft["model"])
                conn = open_connection()
                try:
                    saved_at = save_reply_draft(conn, dict(row), text, login()[0])
                finally:
                    conn.logout()
                gmail_store.set_gmail_draft(email_id, saved_at)
                st.toast("Saved to your Gmail Drafts, in the original thread")
            except Exception as exc:
                st.error(f"Couldn't save to Gmail: {exc}")
        if draft["gmail_draft_id"]:
            st.markdown(f"Saved to your Gmail Drafts at {draft['gmail_draft_id']}, as a reply in this thread. "
                        f"[Open Gmail Drafts]({DRAFTS_URL}) to review and press **Send**. "
                        "Saving again adds another draft.")
    else:
        subject = row["subject"] if row["subject"].lower().startswith("re:") else f"Re: {row['subject']}"
        gmail.link_button("Open in Gmail", width="stretch", url=f"https://mail.google.com/mail/?view=cm&fs=1&to="
                          f"{quote(row['sender'])}&su={quote(subject)}&body={quote(text)}")
    st.caption(f"Drafted by {draft['model']}. Nothing is ever sent by this app.")
