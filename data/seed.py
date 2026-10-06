"""Load data/sample_emails.json into SQLite."""
import json
from pathlib import Path

from db import store

DATASET = Path(__file__).with_name("sample_emails.json")  # Sample emails with correct answers


def seed() -> int:
    """Replace all data with the sample emails."""
    store.init_db()
    emails = json.loads(DATASET.read_text())
    store.reset_emails(emails)
    return len(emails)


def backfill_extras() -> None:
    """After upgrading an older database: copy the sample emails' recipients, formatting and attachments into it."""
    with store.connect() as conn:
        conn.executemany(
            "UPDATE emails SET recipient = ?, html = ?, attachments = ? WHERE id = ? AND gmail_id IS NULL",
            [(e.get("to", store.ME), e.get("html"), json.dumps(e.get("attachments", [])), e["id"])
             for e in json.loads(DATASET.read_text())])


def drop_outdated_results() -> int:
    """Results from an older question set can't be shown with today's questions: forget them so those
    emails show as "not sorted" and Run Jev answers them again. The emails themselves are kept."""
    from triage.schema import QUESTIONS

    keys = [q.key for q in QUESTIONS]  # Every current question must be in a stored answer
    with store.connect() as conn:
        old = [row["email_id"] for row in conn.execute("SELECT email_id, answers_json FROM triage")
               if not all(f'"{k}"' in row["answers_json"] for k in keys)]
        for table, column in (("triage", "email_id"), ("corrections", "email_id"), ("benchmark_runs", "email_id")):
            conn.executemany(f"DELETE FROM {table} WHERE {column} = ?", [(i,) for i in old])
    return len(old)
