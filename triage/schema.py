"""Triage + lead-qualification questions — the single source of truth.

Jev receives these as Choice / Score / Noul questions; the LLM baseline
receives the same labels as a JSON schema, so both models answer the same task.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)  # One typed question for Jev
class Question:
    key: str
    kind: str  # "choice" | "score" | "noul"
    instructions: str
    options: dict[str, str] = field(default_factory=dict)  # choice
    levels: list[str] = field(default_factory=list)  # score


# Choice: what kind of email
CATEGORY = Question("category", "choice", "What kind of business email this is, for our company's shared inbox",
    {
        "lead": "A potential or existing customer interested in buying or expanding: demo, pricing, quote, RFP, trial",
        "customer": "An existing customer needing help: product problems, how-to questions, account changes, renewals",
        "billing": "Invoices, payments, refunds, charges, tax forms or purchase orders",
        "partnership": "Resellers, integrations, referrals, co-marketing or alliances with another company",
        "vendor": "Someone trying to sell their own product or service to us (cold pitch)",
        "recruiting": "Job applications, candidates, interviews, references or recruiters",
        "legal": "Contracts, NDAs, data-protection (GDPR) requests or legal notices",
        "internal": "A colleague at our own company",
        "automated": "Newsletters, webinars, notifications, receipts, auto-replies and other automated mail",
        "spam": "Scams, phishing or unsolicited bulk mail",
    },
)

URGENCY = Question("urgency", "score", "How soon this email needs attention",  # Score: 0 whenever ... 3 right now
    levels=[
        "Whenever: no time pressure at all",
        "This week: should be handled within a few days",
        "Today: needs attention before the end of the day",
        "Right now: needs attention within the hour",
    ],
)

ACTION = Question("action", "choice", "The best next action for us on this email",  # Choice: the best next step
    {
        "reply": "Write a reply to the sender",
        "schedule": "Book a call, demo or meeting",
        "forward": "Hand off to a team or colleague",
        "read_later": "Worth reading, but no action required",
        "archive": "No action or reading needed; just archive",
        "delete": "Junk, spam or phishing; delete it",
    },
)

ROUTE_TO = Question("route_to", "choice", "Which team should own this email",  # Choice: who should own it
    {
        "sales": "Sales: new leads, demos, pricing, quotes, RFPs and expansions",
        "success": "Customer success: help, problems and account questions from existing customers",
        "finance": "Finance: invoices, payments, refunds and tax forms",
        "partnerships": "Partnerships: resellers, integrations, referrals and co-marketing",
        "hr": "HR: candidates, recruiters and references",
        "legal": "Legal: contracts, NDAs, GDPR and legal notices",
        "me": "No team needed: internal, automated, vendor pitches or spam",
    },
)

# Noul questions: yes/no as a probability
NEEDS_REPLY = Question("needs_reply", "noul", "A real person is waiting for a reply from us")
HAS_DEADLINE = Question("has_deadline", "noul", "The email mentions a specific deadline or a time-sensitive request")
RED_FLAG = Question("red_flag", "noul", "The email involves a legal threat, a security issue, a payment problem or a very unhappy customer or prospect")
IS_HUMAN = Question("is_human", "noul", "A person wrote this email personally, rather than an automated system")

# ---- lead qualification: only meaningful for leads, asked in the same call -----------
BUYING_INTENT = Question("buying_intent", "score", "How ready the sender is to buy from us",
    levels=[
        "None: not buying (student, competitor, vendor, test or no interest)",
        "Researching: early interest, gathering information, no plan yet",
        "Evaluating: comparing options, asking for pricing, demos or details",
        "Ready to buy: budget, deadline or decision in place, wants to move now",
    ],
)
# Score: fit with our customer profile
COMPANY_FIT = Question("company_fit", "score", "How well the sender's company matches our ideal customer profile (see our_company)",
    levels=[
        "Poor: individual, student, tiny team or unrelated need",
        "Weak: small company or a need we only partly serve",
        "Good: matches our target size or industry",
        "Strong: matches our target size, industry and buyer role",
    ],
)
DECISION_MAKER = Question("decision_maker", "noul", "The sender can approve the purchase or controls the budget")
BUDGET_MENTIONED = Question("budget_mentioned", "noul", "The email mentions a budget, a price, seats or an approved purchase")
TIMELINE = Question("timeline", "choice", "When the sender wants to start or decide",  # Choice: when they want to start
    {
        "now": "This week or this month",
        "this_quarter": "Within the next three months",
        "later": "Later: next year or after a current contract ends",
        "unknown": "No timeline mentioned",
    },
)

QUESTIONS: list[Question] = [  # Asked together in one Jev call
    CATEGORY, URGENCY, ACTION, ROUTE_TO, NEEDS_REPLY, HAS_DEADLINE, RED_FLAG, IS_HUMAN,
    BUYING_INTENT, COMPANY_FIT, DECISION_MAKER, BUDGET_MENTIONED, TIMELINE,
]
SCORE_FIELDS = ("urgency", "buying_intent", "company_fit")  # answers on a 0-3 scale

# Fields compared against gold labels in evaluation
EVAL_FIELDS = ["category", "urgency", "action", "route_to", "needs_reply", "buying_intent"]


def email_state(email: dict, max_chars: int, profile: str | None = None) -> dict:  # What the model reads (the 'state')
    """The state block both models see: the business profile (the visitor's, else config) and the cleaned email."""
    from triage.config import app_config

    return {
        "our_company": profile or app_config()["company_profile"],
        "email": {"from": email["sender"], "subject": email["subject"], "body": email["body"][:max_chars]},
    }
