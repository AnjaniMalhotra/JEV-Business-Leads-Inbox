"""Connect to Gmail with an app password over IMAP, the standard email protocol. No Google Cloud app is involved.

The address and app password come from the visitor's own browser session; nothing is stored here or on disk.
"""
import imaplib

HOST = "imap.gmail.com"


class LoginError(Exception):
    """Gmail refused the address / app password."""


def connect(address: str, app_password: str) -> imaplib.IMAP4_SSL:
    """Open an encrypted connection and sign in. Close it with .logout() when done."""
    conn = imaplib.IMAP4_SSL(HOST, timeout=30)  # SSL: the password never travels in plain text
    try:
        conn.login(address.strip(), app_password.replace(" ", ""))  # Google shows it with spaces
    except imaplib.IMAP4.error as exc:
        conn.shutdown()
        raise LoginError("Gmail didn't accept this address and app password. Check both, and make sure the "
                         "password is an app password (16 letters), not your normal Google password.") from exc
    return conn


def thread_url(thread_id: str) -> str:  # Opens the conversation in Gmail
    return f"https://mail.google.com/mail/u/0/#all/{thread_id}"
