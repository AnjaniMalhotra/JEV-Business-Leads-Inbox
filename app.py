"""Business Lead Inbox · Gmail — entry point.   .venv/bin/streamlit run app.py"""
import streamlit as st

from ui.sidebar import sidebar

APP_TITLE, APP_ICON = "Business Lead Inbox · Gmail", "📈"  # shown on the browser tab and atop the sidebar
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="expanded")

nav = st.navigation([  # The three pages in the top bar
    st.Page("views/inbox.py", title="Inbox", icon=":material/inbox:", default=True),
    st.Page("views/dashboard.py", title="Dashboard", icon=":material/bar_chart:"),
    st.Page("views/compare.py", title="Compare models", icon=":material/compare_arrows:"),
], position="top")
st.sidebar.markdown(f"## {APP_ICON} {APP_TITLE}")  # App name above the keys
st.sidebar.caption("Jev routes your real business Gmail and finds hot leads")
sidebar()  # API keys + settings on the left
nav.run()  # Show the page the user picked
