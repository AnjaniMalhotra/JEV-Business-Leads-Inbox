"""Demo mode: practice answers so the whole app works before API keys are added.

Answers come from keyword heuristics; latency and token numbers are simulated.
Everything produced here is labelled "mock-*" in the database and the UI."""
from triage.heuristics import guess


def jev_like(email: dict) -> dict:  # Demo Jev: keyword guesses, simulated speed
    result = guess(email)
    rng = result.pop("rng")
    result["latency_ms"] = rng.uniform(90, 380)
    result["output_tokens"] = 0
    return result


def llm_like(email: dict) -> dict:  # Demo LLM: yes/no answers, slower
    result = guess(email)
    rng = result.pop("rng")
    answers = result["answers"]
    answers["urgency"] = float(round(answers["urgency"]))
    for key in ("needs_reply", "has_deadline", "red_flag", "is_human", "decision_maker", "budget_mentioned"):
        answers[key] = 1.0 if answers[key] >= 0.5 else 0.0  # an LLM gives yes/no, not a probability
    for key in ("buying_intent", "company_fit"):
        answers[key] = float(round(answers[key]))
    parse_error = rng.random() < 0.02  # About 2% simulated format errors
    return {
        "answers": None if parse_error else answers,
        "probabilities": {},
        "confidence": {},
        "parse_error": parse_error,
        "error": "Demo: simulated format error" if parse_error else None,
        "latency_ms": rng.uniform(1400, 4200),
        "output_tokens": rng.randint(60, 140) + rng.randint(150, 600),  # answer + thinking
    }


def draft_reply(email: dict, tone: str = "Friendly") -> str:  # Placeholder reply for demo mode
    name = email["sender"].split("@")[0].split(".")[0].title()
    return (
        f"{'Dear' if tone == 'Formal' else 'Hi'} {name},\n\n"
        f"Thanks for your email about \"{email['subject']}\". I've read it and will get back to you "
        "with a full answer shortly.\n\n"
        "Best regards\n\n"
        "[DEMO DRAFT — add an LLM API key in the sidebar for real drafts]"
    )
