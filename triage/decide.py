"""Decision layer: plain Python on top of the model's typed answers.

Priority, buckets, the review gate and the lead score/grade are computed here, never by the model.
"""
from triage.schema import URGENCY

MAX_URGENCY = len(URGENCY.levels) - 1  # Top of the 0-3 scale


# '@domain' matches a whole company, otherwise the exact address
def is_vip(sender: str, vip_senders: list[str]) -> bool:
    sender = sender.lower()
    return any(sender.endswith(v.lower()) if v.startswith("@") else sender == v.lower() for v in vip_senders)


def priority_score(answers: dict, sender: str, cfg: dict) -> float:  # Weighted sum of Jev's answers, 0..1
    w = cfg["priority_weights"]
    return (
        w["urgency"] * (answers["urgency"] / MAX_URGENCY)
        + w["needs_reply"] * answers["needs_reply"]
        + w["red_flag"] * answers["red_flag"]
        + w["has_deadline"] * answers["has_deadline"]
        + w["vip_sender"] * float(is_vip(sender, cfg["vip_senders"]))
    )


def bucket(score: float, answers: dict, cfg: dict) -> str:  # Turn the score into P1-P4
    # Serious issues jump to P1 (except spam)
    if answers["red_flag"] >= cfg["red_flag_override"] and answers["category"] != "spam":
        return "P1"
    for name, threshold in cfg["buckets"].items():
        if score >= threshold:
            return name
    return "P4"


def needs_review(confidence: dict, cfg: dict) -> bool:  # Low confidence: a person should check
    """Low confidence on category or action -> a human decides. Missing = LLM/rules (no gate)."""
    limit = cfg["review_confidence"]
    return any(confidence.get(k, 1.0) < limit for k in ("category", "action"))


def lead_score(answers: dict, cfg: dict) -> float | None:
    """Composite lead score 0..1 from Jev's lead answers (leads only). Weights live in config/app.yaml."""
    if answers["category"] != "lead":
        return None
    w = cfg["lead_weights"]
    return round(
        w["buying_intent"] * answers["buying_intent"] / MAX_URGENCY
        + w["company_fit"] * answers["company_fit"] / MAX_URGENCY
        + w["decision_maker"] * answers["decision_maker"]
        + w["budget_mentioned"] * answers["budget_mentioned"]
        + w["timeline"] * cfg["timeline_value"].get(answers["timeline"], 0.0), 4)


def lead_grade(score: float | None, cfg: dict) -> str | None:  # First grade whose cut-off the score reaches
    if score is None:
        return None
    return next((grade for grade, threshold in cfg["lead_grades"].items() if score >= threshold), "D")


def decide(result: dict, sender: str, cfg: dict) -> dict:  # Every decision for one email, in one place
    answers = result["answers"]
    score = priority_score(answers, sender, cfg)
    lead = lead_score(answers, cfg)
    grade = lead_grade(lead, cfg)
    priority_bucket = bucket(score, answers, cfg)  # Start from the normal priority
    if grade == "A":  # hot lead: always do now
        priority_bucket = "P1"
    elif grade == "B":  # good lead: at least important
        priority_bucket = min(priority_bucket, "P2")
    return {
        "priority": round(score, 4),
        "bucket": priority_bucket,
        "needs_review": needs_review(result.get("confidence", {}), cfg),
        "lead_score": lead,
        "lead_grade": grade,
    }
