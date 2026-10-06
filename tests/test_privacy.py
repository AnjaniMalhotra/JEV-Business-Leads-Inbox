"""Privacy on a shared deployment: every visitor has their own database."""
from db import gmail_store, store
from gmail.fetch import parse
from tests.test_gmail import raw_email
from triage import config


def test_two_visitors_never_see_each_others_emails(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    current = {"db": tmp_path / "visitor-a.db"}
    config.set_db_resolver(lambda: current["db"])    # how the app gives each session its own file
    try:
        store.init_db()
        gmail_store.upsert_gmail_emails([parse(raw_email("Visitor A's secret"), "1", 1)])
        current["db"] = tmp_path / "visitor-b.db"
        store.init_db()
        assert store.emails_df().empty               # visitor B sees nothing of visitor A
        current["db"] = tmp_path / "visitor-a.db"
        assert list(store.emails_df()["subject"]) == ["Visitor A's secret"]
    finally:
        config.set_db_resolver(None)
