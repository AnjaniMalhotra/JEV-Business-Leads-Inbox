"""The Analysis tab: what Jev decided and how sure it was, plus Looks right / Correct it."""
import pandas as pd
import streamlit as st

from db import feedback
from triage.pipeline import triage_email
from ui.labels import (ACTION_LABEL, CATEGORY_LABEL, FIT_LABEL, GRADE, INTENT_LABEL, PRIORITY, ROUTE_LABEL,
                       TIMELINE_LABEL, URGENCY_LABEL, pct, urgency_label)
from ui.jev_key import jev_error
from ui.sidebar import keys


def show_decision(row) -> None:
    email_id = int(row["id"])
    if not row["sorted"]:  # Not analysed yet: offer a button
        st.info("Jev hasn't analysed this email yet.")
        if st.button("Analyse with Jev", type="primary", icon=":material/psychology:"):
            try:
                triage_email({"id": email_id, "sender": row["sender"], "subject": row["subject"], "body": row["body"]}, keys())
            except Exception as exc:
                st.error(jev_error(exc))
            st.rerun()
        return

    a, conf = row["final"], row["confidence"] or {}
    if row["needs_review"]:
        st.warning("Jev isn't confident about this email. Please confirm or correct it.")
    yes = lambda p: "Yes" if p >= 0.5 else "No"  # noqa: E731
    st.dataframe(pd.DataFrame([  # One row per answer, with confidence
        ("Type", CATEGORY_LABEL[a["category"]], pct(conf.get("category"))),
        ("Next step", ACTION_LABEL[a["action"]], pct(conf.get("action"))),
        ("Owner", ROUTE_LABEL[a["route_to"]], pct(conf.get("route_to"))),
        ("Urgency", urgency_label(a["urgency"]), pct(conf.get("urgency"))),
        ("Reply needed", yes(a["needs_reply"]), ""), ("Deadline", yes(a["has_deadline"]), ""),
        ("Serious issue", yes(a["red_flag"]), ""), ("Written by", "A person" if a["is_human"] >= 0.5 else "Automated", ""),
        ("Priority", f"{PRIORITY[row['bucket']][0]} (score {row['priority']:.2f})", ""),
    ] + (lead_rows(row, a, conf) if row["lead_grade"] else []),
        columns=["Field", "Jev's answer", "Confidence"]), hide_index=True, width="stretch")
    probs = (row["probabilities"] or {}).get("category")
    source = ("Sorted by a free rule (auto-reply or bounce), no AI call" if row["source"].startswith("rules")
              else f"{row['model']} · {row['latency_ms'] or 0:.0f} ms · ${row['cost_usd'] or 0:.6f}")
    # Runner-up types Jev considered
    alts = " · Type alternatives: " + ", ".join(f"{CATEGORY_LABEL[k]} {v:.0%}" for k, v in
                                                sorted(probs.items(), key=lambda kv: -kv[1])[1:3]) if probs else ""
    st.caption(source + alts + (" · Corrected by you" if row["corrected"] else ""))

    ok, fix = st.columns([1, 3])
    if ok.button("Looks right", key=f"ok_{email_id}", icon=":material/check:", width="stretch"):
        save_fixes(email_id, a, {})
        st.rerun()
    with fix.expander("Correct it", icon=":material/edit:"):  # Your fix is stored separately
        with st.form(f"fix_{email_id}", border=False):
            f1, f2 = st.columns(2)
            cat = f1.selectbox("Type", list(CATEGORY_LABEL), list(CATEGORY_LABEL).index(a["category"]), format_func=CATEGORY_LABEL.get)
            urg = f2.selectbox("Urgency", range(4), int(round(a["urgency"])), format_func=lambda i: URGENCY_LABEL[i])
            act = f1.selectbox("Next step", list(ACTION_LABEL), list(ACTION_LABEL).index(a["action"]), format_func=ACTION_LABEL.get)
            route = f2.selectbox("Owner", list(ROUTE_LABEL), list(ROUTE_LABEL).index(a["route_to"]), format_func=ROUTE_LABEL.get)
            reply = st.toggle("Someone is waiting for my reply", a["needs_reply"] >= 0.5)
            if st.form_submit_button("Save", type="primary"):
                save_fixes(email_id, a, {"category": cat, "urgency": float(urg), "action": act,
                                         "route_to": route, "needs_reply": 1.0 if reply else 0.0})
                st.rerun()


def lead_rows(row, a: dict, conf: dict) -> list[tuple]:
    """Lead qualification: Jev's lead answers and the lead score code computes from them."""
    level = lambda v: int(round(min(max(v, 0), 3)))  # noqa: E731
    return [("Lead", f"{GRADE[row['lead_grade']][0]} (score {row['lead_score']:.2f})", ""),
            ("Buying intent", INTENT_LABEL[level(a["buying_intent"])], pct(conf.get("buying_intent"))),
            ("Company fit", FIT_LABEL[level(a["company_fit"])], pct(conf.get("company_fit"))),
            ("Decision maker", "Yes" if a["decision_maker"] >= 0.5 else "No", ""),
            ("Budget mentioned", "Yes" if a["budget_mentioned"] >= 0.5 else "No", ""),
            ("Timeline", TIMELINE_LABEL.get(a["timeline"], a["timeline"]), pct(conf.get("timeline")))]


def save_fixes(email_id: int, old: dict, new: dict) -> int:
    """Log only real changes; the model's original answers are never modified."""
    changed = 0
    for field, value in new.items():
        before = old[field]
        if field == "urgency":
            same = round(before) == round(value)
        elif field == "needs_reply":
            same = (before >= 0.5) == (value >= 0.5)
        else:
            same = before == value
        if not same:
            feedback.add_correction(email_id, field, before, value)
            changed += 1
    feedback.mark_reviewed(email_id)
    feedback.set_gold(email_id, {**old, **new})
    st.toast(f"Saved {changed} correction(s)." if changed else "Marked as reviewed.")
    return changed
