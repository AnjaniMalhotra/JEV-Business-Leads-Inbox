"""Plain-language labels and small formatting helpers."""
import pandas as pd

from triage.schema import ACTION, CATEGORY, ROUTE_TO, URGENCY


# Bucket -> (name, chip colour)
PRIORITY = {"P1": ("Do now", "red"), "P2": ("Important", "orange"), "P3": ("Normal", "blue"), "P4": ("Later", "gray")}
CATEGORY_LABEL = {
    "lead": "Lead", "customer": "Customer", "billing": "Billing", "partnership": "Partnership", "vendor": "Vendor pitch",
    "recruiting": "Recruiting", "legal": "Legal", "internal": "Internal", "automated": "Automated", "spam": "Spam",
}
ACTION_LABEL = {
    "reply": "Reply", "schedule": "Book a call", "forward": "Forward",
    "read_later": "Read later", "archive": "Archive", "delete": "Delete",
}
ROUTE_LABEL = {
    "sales": "Sales", "success": "Customer success", "finance": "Finance", "partnerships": "Partnerships",
    "hr": "HR", "legal": "Legal", "me": "Me",
}
TIMELINE_LABEL = {"now": "This month", "this_quarter": "This quarter", "later": "Later", "unknown": "Not mentioned"}
INTENT_LABEL = ["None", "Researching", "Evaluating", "Ready to buy"]
FIT_LABEL = ["Poor", "Weak", "Good", "Strong"]
GRADE = {"A": ("Hot lead", "red"), "B": ("Lead B", "orange"), "C": ("Lead C", "blue"), "D": ("Lead D", "gray")}
URGENCY_LABEL = ["Whenever", "This week", "Today", "Right now"]
assert list(CATEGORY_LABEL) == list(CATEGORY.options)
assert list(ACTION_LABEL) == list(ACTION.options)
assert list(ROUTE_LABEL) == list(ROUTE_TO.options)
assert len(URGENCY_LABEL) == len(URGENCY.levels)

# Chips are grey; colour only where it matters.
TAG_COLOURS = ({name: colour for name, colour in GRADE.values()}
               | {name: "gray" for name in CATEGORY_LABEL.values()}
               | {"Reply needed": "blue", "Serious": "red", "Needs review": "orange"}
               | {name: "gray" for key, name in ROUTE_LABEL.items() if key != "me"})


def tags(row) -> list[tuple[str, str]]:
    """Labels of a sorted email as (text, colour): lead grade or type, reply needed, serious, needs review, team."""
    out = [GRADE[row["lead_grade"]] if row["lead_grade"] in GRADE else (CATEGORY_LABEL[row["category"]], "gray")]
    if row["needs_reply"] >= 0.5:
        out.append(("Reply needed", "blue"))
    if row["red_flag"] >= 0.5:
        out.append(("Serious", "red"))
    if row["needs_review"]:
        out.append(("Needs review", "orange"))
    if row["route_to"] not in ("me", "sales"):  # sales is implied by the lead chip
        out.append((ROUTE_LABEL[row["route_to"]], "gray"))
    return out


def display_name(sender: str) -> str:
    """'priya.shah@bigclient.com' -> 'Priya Shah'; 'no-reply@amazon.in' -> 'Amazon'."""
    local, _, domain = sender.partition("@")
    generic = {"no-reply", "noreply", "notifications", "news", "newsletter", "offers", "deals", "alerts", "digest",
               "mailer-daemon", "postmaster", "hello", "team", "support", "billing", "security", "store", "sales",
               "marketing", "weekly", "verify", "statements", "info", "refunds", "subscriptions", "investments",
               "insurance", "payroll", "finance", "hr", "legal", "ops", "contracts", "procurement", "recruiter"}
    if local.lower() in generic or local.lower().startswith(("no-reply", "calendar-", "fraud-")):
        return domain.split(".")[-2].replace("-", " ").title() if "." in domain else domain
    return " ".join(p.capitalize() for p in local.replace("_", ".").replace("-", ".").split(".") if p)


def urgency_label(value: float) -> str:
    return URGENCY_LABEL[int(round(min(max(value, 0), 3)))]


def when(iso: str) -> str:
    return pd.Timestamp(iso).strftime("%a %d %b, %H:%M")


def short_date(iso: str) -> str:
    return pd.Timestamp(iso).strftime("%d %b")


def money(x: float) -> str:  # Small costs need more decimals
    if x == 0:
        return "$0"
    if x < 0.01:
        return f"${x:.5f}"
    if x < 100:
        return f"${x:,.2f}"
    return f"${x:,.0f}"


def pct(x: float) -> str:  # '–' when there's no value
    return "–" if x is None or pd.isna(x) else f"{x:.0%}"
