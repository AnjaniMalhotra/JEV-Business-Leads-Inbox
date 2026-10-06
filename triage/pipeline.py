"""Triage flow: clean -> rules -> Jev -> decision layer -> store."""
from collections.abc import Callable

from db import store
from triage import jev_client, rules
from triage.config import app_config
from triage.decide import decide
from triage.text import clean_body


def prepare(email: dict) -> dict:
    return {**email, "body": clean_body(email["body"], app_config()["max_body_chars"])}


def triage_email(email: dict, keys: dict) -> dict:
    email = prepare(email)
    ruled = rules.pre_filter(email)  # Step 2: free rules first
    if ruled:
        name, result = ruled
        result.update(model=None, latency_ms=0.0, input_tokens=0, output_tokens=0, cost_usd=0.0)
        source = f"rules:{name}"
    else:
        result = jev_client.classify(email, keys)
        source = "jev"
    decision = decide(result, email["sender"], app_config())  # Step 4: code decides the priority
    store.save_triage(email["id"], source, result, decision)  # Save the answers and the decision
    return {**result, **decision, "source": source}


# Sort many emails, reporting progress
def triage_all(keys: dict, on_progress: Callable[[int, int, dict], None] | None = None,
               only_new: bool = False) -> list[dict]:
    """Sort emails (only the ones not sorted yet, if only_new) and store the results."""
    emails = store.emails_df()
    if only_new:  # Skip emails that already have results
        done = store.inbox_df().dropna(subset=["answers_json"])["id"]
        emails = emails[~emails["id"].isin(done)]
    emails = emails.to_dict("records")
    results = []
    for i, email in enumerate(emails, 1):
        results.append(triage_email(email, keys))
        if on_progress:
            on_progress(i, len(emails), email)
    return results
