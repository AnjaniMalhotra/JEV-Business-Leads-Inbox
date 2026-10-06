"""The Jev key box: check the key once when it changes, show what is really in the box, explain 401 errors."""
import hashlib
import re

import streamlit as st

from triage.jev_client import check_key


APP_PASSWORD = re.compile(r"[a-z]{4}( ?[a-z]{4}){3}")  # what a Google app password looks like


def jev_key_status() -> None:
    """Check the Jev key once when it changes, and show what is really in the box."""
    ss, key = st.session_state, st.session_state.get("jev_key", "").strip()
    if not key:
        ss.pop("jev_status", None)
        return
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    if ss.get("jev_checked") != fingerprint:
        ss.jev_status, ss.jev_checked = check_key(key), fingerprint
    st.caption(f"In the box: `{key[:4]}…{key[-3:]}` ({len(key)} characters)")
    if APP_PASSWORD.fullmatch(key):
        st.warning("This looks like a Gmail app password, not a Jev key. Your browser may have filled it in.")
    elif ss.jev_status == "rejected":
        st.error("TypeSafe rejected this key (401). Clear the box and paste your Jev key again, or create a new one.")
    elif ss.jev_status == "ok":
        st.success("Jev key accepted.")


def jev_error(exc: Exception) -> str:
    """A plain-language message for errors from Jev."""
    if "401" in str(exc):
        return ("TypeSafe rejected the Jev key (401). Clear the Jev box in the sidebar and paste your key again "
                "(browsers sometimes fill in a saved password), or create a new key at typesafe.ai.")
    return f"Jev couldn't sort the emails: {exc}"
