import time

import streamlit as st

from data.seed import seed
from db import gmail_store
from triage.pipeline import triage_all
from ui.data import all_emails, setup
from ui.email_list import email_list
from ui.email_view import open_email
from ui.filters import filters
from ui.gmail_ui import connect_panel, disconnect, fetch_mail, fetch_options, login
from ui.labels import money
from ui.jev_key import jev_error
from ui.sidebar import keys

setup()
df = all_emails()
new = int((~df["sorted"]).sum())  # Emails Jev hasn't read yet


def run_jev(only_new: bool) -> None:  # Sort emails with a progress bar
    if not (new if only_new else len(df)):
        st.toast("Every email is already sorted.")
        return
    bar = st.progress(0.0, text="Jev is reading your emails…")
    start = time.perf_counter()
    try:
        results = triage_all(keys(), lambda i, n, e: bar.progress(i / n, text=f"Jev is reading email {i} of {n}"),
                             only_new=only_new)
    except Exception as exc:  # bad key, network, rate limit…
        bar.empty()
        st.error(jev_error(exc))
        return
    cost = sum(r.get("cost_usd") or 0 for r in results)
    st.session_state.last_run = f"Sorted {len(results)} emails in {time.perf_counter() - start:.1f}s for {money(cost)}."
    st.rerun()


# Header: title left, buttons right
title, fetch_col, run, more = st.columns([5, 1.4, 1.6, 0.5], vertical_alignment="center")
title.header("Inbox")
if fetch_col.button("Fetch mail", icon=":material/sync:", width="stretch", disabled=not login(),
                    help="Get new emails from Gmail (and sort them with Jev)"):
    try:
        st.session_state.last_run = fetch_mail()
    except Exception as exc:
        st.error(f"Couldn't fetch from Gmail: {exc}")
    else:
        st.rerun()
if run.button(f"✨ Run Jev{f' ({new} new)' if new else ''}", type="primary", width="stretch",
              help="Jev reads every email it hasn't seen yet and labels it"):
    run_jev(only_new=True)
with more.popover("", icon=":material/more_horiz:"):  # The ⋯ menu
    st.markdown("**Fetching**")
    fetch_options()
    st.divider()
    if st.button("Sort everything again", icon=":material/refresh:", help="E.g. after adding your Jev key"):
        run_jev(only_new=False)
    if st.button("Load the 100 sample emails", icon=":material/science:", help="Replaces everything in the app"):
        seed()
        st.rerun()
    if st.button("Remove all emails from the app", icon=":material/delete:", help="Your Gmail is not touched"):
        gmail_store.clear_emails()
        st.rerun()
    if login() and st.button("Disconnect Gmail", icon=":material/logout:", help="Forgets the app password in this session"):
        disconnect()
        st.rerun()

if "last_run" in st.session_state:
    st.success(st.session_state.pop("last_run"))
if "jev_problem" in st.session_state:  # fetched fine, but Jev couldn't sort
    st.error(st.session_state.pop("jev_problem"))
if df.empty:  # First visit: connect your own Gmail, or try the sample inbox
    left, right = st.columns([3, 2], gap="large")
    with left.container(border=True):
        connect_panel()
    with right.container(border=True):
        st.markdown("#### Just exploring?")
        st.caption("Try the app with 100 sample business emails. No password needed.")
        if st.button("Try the sample inbox", icon=":material/science:", width="stretch"):
            seed()
            st.rerun()
    st.stop()

done = df[df["sorted"]]
# One-line summary under the title
stats = [f"{len(df)} emails", f"{int((done['lead_grade'] == 'A').sum())} hot leads", f"{int((done['bucket'] == 'P1').sum())} do now",
         f"{int((done['needs_reply'].astype(float) >= 0.5).sum())} awaiting reply",
         f"{int(done['needs_review'].astype(bool).sum())} need review"] + ([f"{new} not sorted"] if new else [])
if "last_fetch" in st.session_state:
    stats.append(f"fetched {st.session_state.last_fetch}")
st.caption(" · ".join(stats))

view = filters(df, "inbox", inbox=True)  # Toolbar: search, priority, filters, sort
if view.empty:
    st.info("No emails match these filters.")
    st.stop()
clicked = email_list(view)  # Click a row to open the email
if clicked is not None:
    open_email(clicked)
