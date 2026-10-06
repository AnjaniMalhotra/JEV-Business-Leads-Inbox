"""Render and click through every page and the email view headlessly (demo mode, temp database)."""
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from db import benchmarks, feedback, store
from tests.conftest import NO_KEYS, ROOT
from triage import benchmark, scoring
from triage.pipeline import triage_all
from ui.safe_html import email_document, remote_images

PAGES = ["views/inbox.py", "views/dashboard.py", "views/compare.py"]


def page(path: str, timeout: int = 90) -> AppTest:  # Run one page headlessly
    return AppTest.from_file(str(ROOT / path), default_timeout=timeout).run()


def button(at: AppTest, prefix: str):  # Find a button by how its label starts
    return next(b for b in at.button if b.label.startswith(prefix))


@pytest.mark.parametrize("path", PAGES)
def test_pages_render_before_and_after_sorting(seeded_db, path):
    assert not page(path).exception
    triage_all(NO_KEYS)
    benchmark.run(store.emails_df().head(10).to_dict("records"), NO_KEYS)
    assert not page(path).exception


def test_app_sidebar_has_keys_dropdown_and_top_nav(seeded_db):
    at = page("app.py")
    assert not at.exception
    labels = [t.label for t in at.sidebar.text_input]
    assert labels[:4] == ["Jev", "Gemini", "OpenAI", "Claude"]
    assert at.session_state["keys"]["provider"] == "Gemini"


def test_run_jev_sorts_only_new_emails(seeded_db):
    at = page("views/inbox.py", 120)
    button(at, "✨ Run Jev (100 new)").click().run()
    assert not at.exception
    assert store.inbox_df()["answers"].notna().all()
    assert button(at, "✨ Run Jev").label == "✨ Run Jev"  # nothing new left


def email_view(email_id: int) -> AppTest:  # Render one email pop-up on its own
    def script(email_id):
        from ui.data import setup
        from ui.email_view import show

        setup()
        show(email_id)

    return AppTest.from_function(script, args=(email_id,), default_timeout=60).run()


def test_email_view_plain_formatted_and_attachments(seeded_db):
    triage_all(NO_KEYS)
    for email_id in (1, 89, 9, 97):  # plain, newsletter with images, image attachment, risky attachment
        at = email_view(email_id)
        assert not at.exception, email_id
    at = email_view(97)
    assert any("Download blocked" in m.value for m in at.markdown)
    assert not any(b.label == "Download" for b in at.get("download_button"))


def test_email_view_confirm_and_reply(seeded_db):
    triage_all(NO_KEYS)
    at = email_view(1)
    button(at, "Looks right").click().run()
    assert not at.exception
    assert store.inbox_df().set_index("id").loc[1, "reviewed"] == 1
    button(at, "Draft reply").click().run()
    assert not at.exception
    assert "DEMO DRAFT" in feedback.get_draft(1)["text"]


def test_unsorted_email_can_be_sent_to_jev(seeded_db):
    at = email_view(5)
    button(at, "Analyse with Jev").click().run()
    assert not at.exception
    assert store.inbox_df().set_index("id").loc[5, "answers"] is not None


def test_email_html_is_made_safe():
    raw = ('<p onclick="steal()">Hi</p><script>alert(1)</script><a href="javascript:x()">x</a>'
           '<img src="https://tracker.example.com/p.gif">')
    doc = email_document(raw, "", show_images=False)
    assert "alert" not in doc and "onclick" not in doc and "javascript:" not in doc
    assert "img-src data:;" in doc and "script-src" not in doc  # default-src 'none' blocks scripts
    assert "https:" in email_document(raw, "", show_images=True)
    assert remote_images(raw) == 1


def test_compare_models(seeded_db):
    triage_all(NO_KEYS)
    at = page("views/compare.py", 120)
    at.multiselect[0].set_value(["Gemini · gemini-3.8-flash", "OpenAI · gpt-5.6-luna"]).run()
    button(at, "Compare on").click().run()
    assert not at.exception
    assert any("faster" in s.value for s in at.success)
    assert set(scoring.load_scored(benchmarks.benchmark_runs()["run_id"].iloc[0])["mode"]) == {
        "jev", "Gemini · gemini-3.8-flash", "OpenAI · gpt-5.6-luna"}


def test_old_database_is_upgraded(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    monkeypatch.setenv("DB_PATH", str(path))
    with sqlite3.connect(path) as conn:  # the email table as it was before this version
        conn.execute("CREATE TABLE emails (id INTEGER PRIMARY KEY, sender TEXT NOT NULL, subject TEXT NOT NULL, "
                     "body TEXT NOT NULL, received_at TEXT NOT NULL, tags TEXT DEFAULT '', gold_category TEXT, "
                     "gold_urgency INTEGER, gold_action TEXT, gold_route_to TEXT, gold_needs_reply INTEGER)")
        conn.execute("INSERT INTO emails (id, sender, subject, body, received_at) VALUES (89, 'a@b.c', 's', 'b', '2026-09-01')")
    from ui.data import setup

    setup()
    row = store.emails_df().set_index("id").loc[89]
    assert row["html"] and row["recipient"] == "hello@northwind.io"
