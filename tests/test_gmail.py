"""Gmail parts, fully offline: fake IMAP server, temp databases, demo mode."""
import imaplib
from email.message import EmailMessage

import pytest
from streamlit.testing.v1 import AppTest

from db import feedback, gmail_store, store
from gmail import client
from gmail.drafts import save_reply_draft
from gmail.fetch import fetch, parse
from tests.conftest import NO_KEYS, ROOT
from triage.pipeline import triage_all
from triage.rules import pre_filter


def raw_email(subject="Contract question", headers=None) -> bytes:  # A real-looking email with HTML + attachment
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = "Priya Shah <priya@bigclient.com>", "Me <me@x.com>", subject
    m["Message-ID"], m["Date"] = "<m1@mail>", "Mon, 05 Oct 2026 10:00:00 +0000"
    for k, v in (headers or {}).items():
        m[k] = v
    m.set_content("Hi there, can you review the contract?")
    m.add_alternative("<style>p{}</style><p>Hi <b>there</b></p>", subtype="html")
    m.add_attachment(b"%PDF-1.4 tiny", maintype="application", subtype="pdf", filename="contract.pdf")
    return m.as_bytes()


class FakeImap:  # stands in for imaplib.IMAP4_SSL
    def __init__(self, n=3):
        self.n, self.readonly, self.appended = n, None, None

    def select(self, box, readonly=False):
        self.readonly = readonly
        return "OK", [b"3"]

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            return "OK", [b" ".join(str(i).encode() for i in range(1, self.n + 1))]
        uid = int(args[0])
        return "OK", [(f"{uid} (X-GM-MSGID 10{uid} X-GM-THRID 255 BODY[] {{1}}".encode(), raw_email(f"Email {uid}"))]

    def list(self):
        return "OK", [b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Brouillons"']

    def append(self, folder, flags, when, message):
        self.appended = (folder, flags, message.decode())
        return "OK", [b""]


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    store.init_db()


def test_parse_keeps_text_html_thread_and_attachments():
    e = parse(raw_email(headers={"List-Unsubscribe": "<mailto:x>"}), "101", 255)
    assert (e["sender"], e["recipient"], e["thread_id"], e["message_id"]) == ("priya@bigclient.com", "me@x.com", "ff", "<m1@mail>")
    assert e["body"].strip() == "Hi there, can you review the contract?" and "p{}" not in e["html"]
    assert e["attachments"][0]["name"] == "contract.pdf" and "data" in e["attachments"][0]
    assert e["tags"] == ["bulk"] and e["received_at"].startswith("2026-10-05")


def test_fetch_is_read_only_and_newest_first():
    conn = FakeImap(n=5)
    emails = fetch(conn, "newer_than:7d", 3)
    assert conn.readonly is True                      # the mailbox is opened read-only
    assert [e["subject"] for e in emails] == ["Email 5", "Email 4", "Email 3"]


def test_auto_submitted_header_is_settled_by_rules():
    e = parse(raw_email(headers={"Auto-Submitted": "auto-replied"}), "1", 1)
    assert pre_filter({**e, "tags": ",".join(e["tags"])})[0] == "auto_reply"


def test_reply_draft_goes_into_drafts_folder_and_thread():
    conn = FakeImap()
    save_reply_draft(conn, parse(raw_email(), "101", 255), "Thanks, will review.", "me@x.com")
    folder, flags, message = conn.appended
    assert folder == '"[Gmail]/Brouillons"' and flags == "\\Draft"   # found by its \Drafts flag, any language
    assert "In-Reply-To: <m1@mail>" in message and "Subject: Re: Contract question" in message
    assert "text/html" in message and "<p>Thanks, will review.</p>" in message  # rich text: no hard wrapping in Gmail


def test_wrong_app_password_gives_a_clear_error(monkeypatch):
    class Refuses:
        def __init__(self, *a, **k): ...
        def login(self, *a): raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")
        def shutdown(self): ...
    monkeypatch.setattr(client.imaplib, "IMAP4_SSL", Refuses)
    with pytest.raises(client.LoginError, match="app password"):
        client.connect("me@gmail.com", "abcd efgh ijkl mnop")


def test_fetch_twice_no_duplicates_and_sort_only_new(empty_db):
    assert gmail_store.upsert_gmail_emails(fetch(FakeImap(n=2), "x", 10)) == 2
    assert gmail_store.upsert_gmail_emails(fetch(FakeImap(n=2), "x", 10)) == 0
    assert len(triage_all(NO_KEYS, only_new=True)) == 2


def test_checked_emails_become_the_answer_key(empty_db):
    gmail_store.upsert_gmail_emails(fetch(FakeImap(n=1), "x", 10))
    triage_all(NO_KEYS)
    first = store.inbox_df().iloc[0]
    feedback.set_gold(int(first["id"]), first["answers"])
    assert store.emails_df()["gold_category"].notna().sum() == 1


@pytest.mark.parametrize("path", ["views/inbox.py", "views/dashboard.py", "views/compare.py"])
def test_pages_with_gmail_emails(empty_db, path):
    at = AppTest.from_file(str(ROOT / path), default_timeout=60).run()
    assert not at.exception  # empty inbox: connect panel + sample button
    gmail_store.upsert_gmail_emails(fetch(FakeImap(n=5), "x", 10))
    triage_all(NO_KEYS)
    assert not AppTest.from_file(str(ROOT / path), default_timeout=60).run().exception
