"""What you add: fixes to Jev's answers, emails you checked, and reply drafts."""
import json

from db.store import connect, now


def add_correction(email_id: int, field: str, old, new) -> None:  # Log a fix; Jev's answer stays untouched
    """Log a human fix. The model's original answers are never modified."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO corrections (email_id, field, old_value, new_value, created_at) VALUES (?, ?, ?, ?, ?)",
            (email_id, field, json.dumps(old), json.dumps(new), now()),
        )


def mark_reviewed(email_id: int) -> None:  # Takes the email out of Needs review
    with connect() as conn:
        conn.execute("UPDATE triage SET reviewed = 1 WHERE email_id = ?", (email_id,))


def save_draft(email_id: int, text: str, status: str, model: str | None) -> None:  # Keep the latest draft per email
    """Save the local draft (keeps the link to its Gmail draft, if any)."""
    with connect() as conn:
        conn.execute(
            """INSERT INTO drafts (email_id, text, status, model, created_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(email_id) DO UPDATE SET text = excluded.text, status = excluded.status,
               model = excluded.model, created_at = excluded.created_at""",
            (email_id, text, status, model, now()),
        )


def set_gold(email_id: int, answers: dict) -> None:
    """Real emails have no answer key: the answers you confirm or correct become this email's correct answers."""
    with connect() as conn:
        conn.execute(
            """UPDATE emails SET gold_category = ?, gold_urgency = ?, gold_action = ?, gold_route_to = ?,
               gold_needs_reply = ? WHERE id = ?""",
            (answers["category"], int(round(answers["urgency"])), answers["action"], answers["route_to"],
             int(answers["needs_reply"] >= 0.5), email_id),
        )


def get_draft(email_id: int) -> dict | None:  # Latest draft, or None
    with connect() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE email_id = ?", (email_id,)).fetchone()
    return dict(row) if row else None
