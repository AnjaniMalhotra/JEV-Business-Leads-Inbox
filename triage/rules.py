"""Header/sender rules that settle obvious emails without calling any model."""

# Subjects of automatic replies
AUTO_REPLY_SUBJECTS = ("out of office", "automatic reply", "auto:", "autoreply", "on vacation")
# Subjects of delivery failures
BOUNCE_SUBJECTS = ("undeliverable", "delivery status notification", "mail delivery failed", "returned mail")
BOUNCE_SENDERS = ("mailer-daemon", "postmaster")


def _rule_answer(action: str) -> dict:  # Ready-made answer: archive, no reply needed
    return {
        "answers": {
            "category": "automated",
            "urgency": 0.0,
            "action": action,
            "route_to": "me",
            "needs_reply": 0.0,
            "has_deadline": 0.0,
            "red_flag": 0.0,
            "is_human": 0.0,
            "buying_intent": 0.0, "company_fit": 0.0, "decision_maker": 0.0, "budget_mentioned": 0.0,
            "timeline": "unknown",
        },
        "probabilities": {},
        "confidence": {"category": 1.0, "action": 1.0, "route_to": 1.0, "urgency": 1.0},
    }


def pre_filter(email: dict) -> tuple[str, dict] | None:
    """Return (rule_name, triage_result) when a rule decides, else None."""
    subject = email["subject"].lower()
    sender = email["sender"].lower()
    if any(s in sender for s in BOUNCE_SENDERS) or subject.startswith(BOUNCE_SUBJECTS):  # Bounces
        return "bounce", _rule_answer("archive")
    if subject.startswith(AUTO_REPLY_SUBJECTS) or "auto-submitted" in (email.get("tags") or ""):  # Auto-replies
        return "auto_reply", _rule_answer("archive")
    return None
