"""SQLite access: emails and Jev's results. Every write opens its own short connection (safe with Streamlit threads)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from triage.config import db_path

SCHEMA = Path(__file__).with_name("schema.sql")  # Table definitions


def now() -> str:  # UTC timestamp for every write
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_json(value, empty=None):  # JSON text from SQLite to Python (or a default)
    return json.loads(value) if isinstance(value, str) else empty


def connect() -> sqlite3.Connection:  # Short-lived connection per call
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


ME = "hello@northwind.io"  # the sample inbox (Gmail emails keep their real To: address)
NEW_COLUMNS = {  # added to older databases on start-up
    "emails": {"recipient": f"TEXT DEFAULT '{ME}'", "html": "TEXT", "attachments": "TEXT DEFAULT '[]'",
               "gmail_id": "TEXT", "thread_id": "TEXT", "message_id": "TEXT",
               "gold_buying_intent": "INTEGER"},
    "drafts": {"gmail_draft_id": "TEXT"},
}


def init_db() -> bool:
    """Create tables and add missing columns. Returns True when sample-email extras need backfilling."""
    added = []
    with connect() as conn:
        conn.executescript(SCHEMA.read_text())
        for table, columns in NEW_COLUMNS.items():
            have = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for col in columns.keys() - have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {columns[col]}")
                added.append(col)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_gmail_id ON emails(gmail_id)")  # one row per Gmail message
    return "html" in added


def reset_emails(emails: list[dict]) -> None:
    """Replace the dataset and everything derived from it."""
    with connect() as conn:
        for table in ("benchmark_runs", "drafts", "corrections", "triage", "emails"):
            conn.execute(f"DELETE FROM {table}")
        conn.executemany(
            """INSERT INTO emails (id, sender, subject, body, received_at, tags, recipient, html, attachments,
               gold_category, gold_urgency, gold_action, gold_route_to, gold_needs_reply, gold_buying_intent)
               VALUES (:id, :sender, :subject, :body, :received_at, :tags, :recipient, :html, :attachments,
               :gold_category, :gold_urgency, :gold_action, :gold_route_to, :gold_needs_reply, :gold_buying_intent)""",
            [
                {
                    **{k: e[k] for k in ("id", "sender", "subject", "body", "received_at")},
                    "tags": ",".join(e.get("tags", [])),
                    "recipient": e.get("to", ME),
                    "html": e.get("html"),
                    "attachments": json.dumps(e.get("attachments", [])),
                    **{f"gold_{k}": v for k, v in e["gold"].items()},
                }
                for e in emails
            ],
        )


def emails_df() -> pd.DataFrame:  # All emails, newest first
    with connect() as conn:
        return pd.read_sql("SELECT * FROM emails ORDER BY received_at DESC", conn)


def save_triage(email_id: int, source: str, result: dict, decision: dict) -> None:  # Original answers + decision
    with connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO triage (email_id, source, model, answers_json, probabilities_json,
               confidence_json, priority, bucket, needs_review, reviewed, latency_ms, input_tokens,
               output_tokens, cost_usd, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
            (
                email_id, source, result.get("model"), json.dumps(result["answers"]),
                json.dumps(result.get("probabilities", {})), json.dumps(result.get("confidence", {})),
                decision["priority"], decision["bucket"], int(decision["needs_review"]),
                result.get("latency_ms"), result.get("input_tokens"), result.get("output_tokens"),
                result.get("cost_usd"), now(),
            ),
        )


def inbox_df() -> pd.DataFrame:
    """Emails joined with their triage.

    `answers` is the model's original output (used for accuracy);
    `final` is answers with the latest human fixes applied (used by the inbox).
    """
    with connect() as conn:
        df = pd.read_sql(
            "SELECT e.*, t.* FROM emails e LEFT JOIN triage t ON t.email_id = e.id ORDER BY e.received_at DESC",
            conn,
        )
        fixes = conn.execute("SELECT email_id, field, new_value FROM corrections ORDER BY id").fetchall()
    df = df.loc[:, ~df.columns.duplicated()]
    for col in ("answers_json", "probabilities_json", "confidence_json"):
        df[col.removesuffix("_json")] = df[col].map(parse_json)

    overrides: dict[int, dict] = {}
    for row in fixes:
        overrides.setdefault(row["email_id"], {})[row["field"]] = json.loads(row["new_value"])
    df["final"] = [{**a, **overrides.get(i, {})} if a else None for i, a in zip(df["id"], df["answers"])]
    df["corrected"] = df["id"].isin(overrides.keys())
    return df
