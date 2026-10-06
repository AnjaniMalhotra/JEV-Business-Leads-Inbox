"""Loading emails for the pages: every email, with priority and labels from the current settings."""
import os
import tempfile
import time
from pathlib import Path

import pandas as pd
from streamlit.runtime.scriptrunner import get_script_run_ctx

from db import store
from triage import config
from triage.decide import decide
from ui.labels import display_name
from ui.sidebar import session_config


SESSIONS = Path(tempfile.gettempdir()) / "smart-inbox-sessions"  # one private database per visitor
KEEP_HOURS = 12


def session_db() -> Path | None:
    """This visitor's own database file (None outside the app, or when tests set DB_PATH)."""
    ctx = get_script_run_ctx()
    if os.getenv("DB_PATH") or ctx is None:
        return None
    SESSIONS.mkdir(exist_ok=True)
    return SESSIONS / f"{ctx.session_id}.db"


def clean_old_sessions() -> None:
    """Delete databases of visitors who left more than KEEP_HOURS ago."""
    for f in SESSIONS.glob("*.db"):
        if time.time() - f.stat().st_mtime > KEEP_HOURS * 3600:
            f.unlink(missing_ok=True)


config.set_db_resolver(session_db)


def setup() -> None:
    """Make sure the database exists and is up to date. Emails come from Gmail (or the samples) via the Inbox."""
    from data.seed import backfill_extras, drop_outdated_results

    if store.init_db():
        backfill_extras()
    if SESSIONS.exists():
        clean_old_sessions()
    drop_outdated_results()


# Answers copied onto each row for the screens
LABEL_FIELDS = ("category", "action", "route_to", "urgency", "needs_reply", "red_flag", "has_deadline",
                "buying_intent", "company_fit", "decision_maker", "budget_mentioned", "timeline")
DECISION_COLUMNS = ("priority", "bucket", "needs_review", "lead_score", "lead_grade", *LABEL_FIELDS)


def decision_for(row, cfg: dict) -> dict:
    """Priority and labels for one email, from its final answers (Jev's answers plus your corrections)."""
    if not row["sorted"]:
        return dict.fromkeys(DECISION_COLUMNS)  # not sorted yet: no labels
    d = decide({"answers": row["final"], "confidence": row["confidence"] or {}}, row["sender"], cfg)
    return {"priority": d["priority"], "bucket": d["bucket"], "lead_score": d["lead_score"], "lead_grade": d["lead_grade"],
            "needs_review": d["needs_review"] and not bool(row["reviewed"]),  # reviewed emails leave the queue
            **{key: row["final"].get(key) for key in LABEL_FIELDS}}


def all_emails() -> pd.DataFrame:
    """Every email, with priority and labels recomputed from the current settings (so Settings apply instantly)."""
    cfg = session_config()
    df = store.inbox_df()
    df["sorted"] = df["final"].notna()  # Has Jev (or a rule) answered yet?
    df["name"] = df["sender"].map(display_name)
    df["n_attachments"] = df["attachments"].map(lambda a: len(store.parse_json(a, [])))
    decisions = pd.DataFrame([decision_for(row, cfg) for _, row in df.iterrows()], index=df.index,
                             columns=DECISION_COLUMNS, dtype=object)
    return pd.concat([df.drop(columns=[c for c in DECISION_COLUMNS if c in df]), decisions], axis=1)


def triaged_inbox() -> pd.DataFrame:
    """Only the sorted emails."""
    df = all_emails()
    return df[df["sorted"]].copy()
