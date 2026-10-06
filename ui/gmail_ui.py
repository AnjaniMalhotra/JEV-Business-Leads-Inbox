"""Gmail in the UI: connect with an app password (kept only in this session), fetch and sort, and the guide."""
from datetime import datetime

import streamlit as st

from db import gmail_store
from gmail import client
from gmail.fetch import fetch
from triage.pipeline import triage_all
from ui.sidebar import keys

GUIDE = """
**Why an app password?** This app reads your Gmail through IMAP, the standard way mail apps (Apple Mail,
Outlook, Thunderbird) connect to Gmail. Google lets such apps sign in only with an **app password**: a
separate 16-letter key for one app. Your real Google password is never used, and you can switch the key
off at any time.

**Get one (about 2 minutes):**
1. Turn on **2-Step Verification**: [myaccount.google.com/security](https://myaccount.google.com/security)
   → *2-Step Verification*. Google only offers app passwords with it switched on.
2. Open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), type a name such as
   *Business Lead Inbox* and click **Create**.
3. Copy the 16-letter password Google shows (e.g. `abcd efgh ijkl mnop`) and paste it here.

**What this app does with it:**
- Keeps it **only in this browser session**, in memory: never saved to disk, never logged, never shared.
  Closing the tab or clicking *Disconnect* forgets it.
- Uses it only to **read** your inbox (emails stay unread) and to **save reply drafts** in your Drafts.
  It never sends, deletes or moves anything.
- Your fetched emails go into a private space for this session only, deleted within 12 hours.

**Switch it off anytime:** [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) →
🗑️ next to the name you chose. It stops working immediately.

*Can't create one?* Some work accounts have app passwords turned off by their admin, and Google's Advanced
Protection accounts can't use them. You can still try the app with the sample inbox.
"""


def login() -> tuple[str, str] | None:
    """(address, app password) for this session, if connected."""
    return st.session_state.get("gmail_login")


def disconnect() -> None:
    for key in ("gmail_login", "gmail_account"):
        st.session_state.pop(key, None)


def open_connection():
    """A fresh IMAP connection for this visitor; the caller closes it with .logout()."""
    address, password = login()
    return client.connect(address, password)


def fetch_options() -> None:
    """Shown in the Inbox's ⋯ menu."""
    st.text_input("Which emails", "newer_than:7d", key="gmail_query",
                  help="Gmail search, e.g. `is:unread`, `newer_than:2d` or `from:priya@bigretail.com`")
    st.number_input("At most", 5, 200, 30, 5, key="gmail_limit")
    st.toggle("Sort new emails with Jev right away", True, key="gmail_autosort")


def fetch_mail() -> str:
    """Fetch from this visitor's Gmail, store, and (optionally) sort the new emails. Returns a one-line summary."""
    ss = st.session_state
    with st.spinner("Fetching from Gmail…"):
        conn = open_connection()
        try:
            emails = fetch(conn, ss.get("gmail_query", "newer_than:7d"), int(ss.get("gmail_limit", 30)))
        finally:
            conn.logout()
        new = gmail_store.upsert_gmail_emails(emails)  # Duplicates are skipped
    ss.last_fetch = datetime.now().strftime("%H:%M")
    summary = f"Fetched {len(emails)} emails from Gmail, {new} new."
    if new and ss.get("gmail_autosort", True):  # Sort the new ones straight away
        bar = st.progress(0.0, text="Jev is reading the new emails…")
        triage_all(keys(), lambda i, n, e: bar.progress(i / n, text=f"Jev is reading email {i} of {n}"), only_new=True)
        summary += f" Jev sorted {new}."
    return summary


def connect_panel() -> None:
    """Connect your own Gmail with an app password, with the step-by-step guide."""
    st.markdown("#### Connect your Gmail")
    st.caption("Your inbox, sorted by Jev. You need a Gmail **app password**; the guide below shows how.")
    with st.form("gmail_connect"):
        address = st.text_input("Gmail address", placeholder="you@gmail.com")
        password = st.text_input("App password (16 letters)", type="password", placeholder="abcd efgh ijkl mnop")
        go = st.form_submit_button("Connect and fetch", type="primary", icon=":material/mail:")
    with st.expander("How do I get an app password, and why does the app need it?", icon=":material/help:"):
        st.markdown(GUIDE)
    if go:
        if not address.strip() or not password.strip():
            st.error("Please enter your Gmail address and the app password.")
            return
        st.session_state.gmail_login = (address.strip(), password.strip())  # this session only
        try:
            st.session_state.gmail_account = address.strip()
            st.session_state.last_run = fetch_mail()
        except client.LoginError as exc:
            disconnect()
            st.error(str(exc))
            return
        except Exception as exc:  # network, IMAP not available…
            disconnect()
            st.error(f"Couldn't connect to Gmail: {exc}")
            return
        st.rerun()
