"""Keyword guesses behind demo mode. Not AI: just enough to make every page work without API keys."""
import math
import random
import re

from triage.schema import ACTION, CATEGORY

KEYWORDS = {  # Words that hint at each answer
    "lead": ["demo", "pricing", "quote", "rfp", "proposal", "budget", "seats", "trial", "evaluat", "sign", "cost",
             "plan", "buy", "platform", "renewal with", "tender"],
    "customer": ["not loading", "error", "how do i", "sso", "feature request", "add three", "add 3", "outage",
                 "training", "rate limit", "our account", "onboarding", "leak", "renewal is"],
    "billing": ["invoice", "charged", "refund", "payment", "w-9", "po number", "overdue", "billing contact"],
    "partnership": ["partner", "reseller", "integration", "co-host", "marketplace", "go-to-market", "introducing"],
    "vendor": ["we can get", "from $", "buy our", "sponsorship", "upgrade your", "translate", "growth agency",
               "ai sales assistant"],
    "recruiting": ["apply", "cv", "candidate", "interview", "reference check", "offer accepted"],
    "legal": ["nda", "gdpr", "data processing", "cease and desist", "trademark", "personal data"],
    "internal": ["standup", "launch plan", "travel policy", "pipeline review", "board call"],
    "automated": ["newsletter", "webinar", "unsubscribe", "assigned to you", "invited", "searches this week",
                  "out of the office", "couldn't be delivered"],
    "spam": ["password expires", "click here", "lottery", "gift cards", "bank details", "trading bot", "pay immediately"],
}
# Which team owns each email type
ROUTE = {"lead": "sales", "customer": "success", "billing": "finance", "partnership": "partnerships",
         "recruiting": "hr", "legal": "legal"}
# Words that mean act now
URGENT = ["asap", "urgent", "immediately", "right now", "today", "this morning", "blocked", "can sign today"]
SOON = ["this week", "by friday", "tomorrow", "deadline", "monday", "due", "end of the month", "thursday"]
RED = ["legal action", "leak", "security issue", "cancel", "disappointing", "overdue", "cease and desist", "outage"]
# Job titles that can approve a purchase
DECIDERS = ["cto", "cfo", "coo", "cio", "vp ", "head of", "director", "founder", "procurement"]
AUTOMATED = ["no-reply", "noreply", "notifications@", "newsletter", "webinars@", "mailer-daemon", "calendar-"]


def _hits(text: str, words: list[str]) -> int:  # How many of the words appear in the text
    return sum(1 for w in words if w in text)


def _softmax(scores: dict[str, float]) -> dict[str, float]:  # Scores to probabilities that add up to 1
    exps = {k: math.exp(v) for k, v in scores.items()}
    return {k: v / sum(exps.values()) for k, v in exps.items()}


def _lead(text: str) -> dict:
    """Lead answers from simple signals: employee count, job title, money and time words."""
    if any(w in text for w in ("student", "thesis", "just browsing", "test test", "competitor")):
        intent = 0
    elif any(w in text for w in ("budget is ready", "budget approved", "can sign", "wants to buy", "rfp", "decide by",
                                 "this month", "tender", "by december", "pilot", "40 more seats", "60 seats")):
        intent = 3
    elif any(w in text for w in ("pricing", "quote", "demo", "evaluat", "comparing", "integrate", "cost", "discount")):
        intent = 2
    else:
        intent = 1
    size = re.search(r"([\d,]+) (?:employees|people)", text)  # Employee count, e.g. '900 people'
    people = int(size.group(1).replace(",", "")) if size else 0
    # Ideal customers have 200-5,000 employees
    fit = 3 if 200 <= people <= 5000 else 2 if people > 5000 else 1 if people >= 50 else 0
    timeline = ("now" if _hits(text, ["today", "this week", "this month", "friday", "monday", "tomorrow", "asap"])
                else "this_quarter" if _hits(text, ["this quarter", "next month", "two weeks", "q4", "end of the month"])
                else "later" if _hits(text, ["next year", "2027", "next summer", "january", "q1"]) else "unknown")
    return {"buying_intent": float(intent), "company_fit": float(fit),
            "decision_maker": 0.85 if _hits(text, DECIDERS) else 0.2,
            "budget_mentioned": 0.85 if _hits(text, ["budget", "$", "seats", "price", "pricing", "quote"]) else 0.1,
            "timeline": timeline}


def guess(email: dict) -> dict:  # Plausible fake answers for demo mode
    text = f"{email['sender']} {email['subject']} {email['body']}".lower()
    rng = random.Random(f"{email.get('id')}-{email['subject']}")  # Seeded, so demo answers never change
    scores = {c: 2.4 * _hits(text, KEYWORDS.get(c, [])) + rng.uniform(0, 0.4) for c in CATEGORY.options}
    if email["sender"].endswith("@northwind.io") and not email["sender"].startswith("forms@"):
        scores["internal"] += 3
    probs = _softmax(scores)
    category = max(probs, key=probs.get)
    is_human = 0.15 if _hits(email["sender"].lower(), AUTOMATED) else 0.85
    urgent, soon = _hits(text, URGENT), _hits(text, SOON)
    quiet = category in ("automated", "spam", "vendor")
    urgency = 0.1 if quiet else min(3.0, 0.3 + 1.1 * urgent + 0.6 * soon)
    needs_reply = 0.15 if quiet or category == "internal" and "?" not in email["body"] else 0.8
    action = ("delete" if category == "spam" else "archive" if category in ("automated", "vendor")
              else "forward" if category in ("billing", "legal", "recruiting") and needs_reply < 0.5
              else "schedule" if _hits(text, ["call", "demo", "meeting", "session", "minutes"]) else
              "reply" if needs_reply > 0.5 else "read_later")
    act_probs = {k: 0.04 for k in ACTION.options}  # Fake confidence: almost all on the chosen action
    act_probs[action] = 1 - 0.04 * (len(act_probs) - 1)
    lead = _lead(text) if category == "lead" else {"buying_intent": 0.0, "company_fit": 0.0, "decision_maker": 0.1,
                                                     "budget_mentioned": 0.1, "timeline": "unknown"}
    return {
        "answers": {"category": category, "urgency": round(urgency, 3), "action": action,
                    "route_to": ROUTE.get(category, "me"), "needs_reply": needs_reply,
                    "has_deadline": min(0.95, 0.1 + 0.4 * (urgent + soon)),
                    "red_flag": 0.1 if category == "spam" else min(0.95, 0.05 + 0.4 * _hits(text, RED)),
                    "is_human": is_human, **lead},
        "probabilities": {"category": probs, "action": act_probs},
        "confidence": {"category": round(probs[category], 3), "action": round(min(0.95, 0.5 + 0.45 * probs[category]), 3),
                       "route_to": round(probs[category], 3), "urgency": 0.6},
        "rng": rng,
    }
