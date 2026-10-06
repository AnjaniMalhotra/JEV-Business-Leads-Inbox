"""The Accuracy tab: score per question, where Jev mixes up types, and whether its confidence can be trusted."""
import altair as alt
import pandas as pd
import streamlit as st

from triage.schema import EVAL_FIELDS
from triage.scoring import field_correct
from ui.labels import ACTION_LABEL, CATEGORY_LABEL

# Short names for the scored questions
QUESTION = {"category": "Type", "urgency": "Urgency", "action": "Next step", "route_to": "Owner",
            "needs_reply": "Reply needed", "buying_intent": "Buying intent"}
HARD = ("phishing", "injection", "tricky")  # sample-email tags worth pointing out


def show_accuracy(df: pd.DataFrame) -> None:
    lab = df[df["gold_category"].notna() & df["answers"].notna()].copy()  # Emails with a known correct answer
    if lab.empty:
        st.info("No emails with a known correct answer yet. Open emails and click **Looks right** or **Correct it** "
                "in the Analysis tab; each one you check is scored here.")
        return
    for f in EVAL_FIELDS:
        lab[f"ok_{f}"] = [field_correct(f, a.get(f), g) for a, g in zip(lab["answers"], lab[f"gold_{f}"])]
    st.caption(f"Jev's own answers (before your corrections) vs the correct answers, on {len(lab)} emails. "
               "Real emails have no answer key: each one you confirm or correct becomes one.")
    cols = st.columns(len(EVAL_FIELDS) + 1)
    cols[0].metric("Overall", f"{lab[[f'ok_{f}' for f in EVAL_FIELDS]].to_numpy().mean():.0%}")
    for col, f in zip(cols[1:], EVAL_FIELDS):
        col.metric(QUESTION[f], f"{lab[f'ok_{f}'].mean():.0%}")

    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("**Where Jev mixes up email types**")
        st.caption("Rows: correct type. Columns: Jev's answer. Off-diagonal cells are mix-ups.")
        cm = pd.DataFrame({"Correct": lab["gold_category"].map(CATEGORY_LABEL),  # Correct type vs Jev's type
                           "Jev": lab["answers"].map(lambda a: CATEGORY_LABEL[a["category"]])})
        cm = cm.value_counts().reset_index(name="Emails")
        order = list(CATEGORY_LABEL.values())
        base = alt.Chart(cm).encode(x=alt.X("Jev:N", sort=order, title="Jev's answer", axis=alt.Axis(labelAngle=-30)),
                                    y=alt.Y("Correct:N", sort=order))
        st.altair_chart((base.mark_rect().encode(color=alt.Color("Emails:Q", scale=alt.Scale(scheme="teals"), legend=None))
                         + base.mark_text(fontSize=12).encode(text="Emails:Q")).properties(height=300), width="stretch")
    with right.container(border=True):
        st.markdown("**Can you trust Jev's confidence?**")
        st.caption("Share of correct types, grouped by Jev's confidence. Rising bars mean high-confidence answers "
                   "are safe to automate and low-confidence ones belong in Needs review.")
        # Jev's confidence vs actually right
        cal = pd.DataFrame({"conf": lab["confidence"].map(lambda c: (c or {}).get("category")),
                            "Correct": lab["ok_category"].astype(float)}).dropna()
        if cal.empty:
            st.caption("No confidence scores yet (rule-sorted emails don't have one).")
        else:
            cal["Confidence"] = pd.cut(cal["conf"], [0, 0.5, 0.7, 0.85, 0.95, 1.0001],
                                       labels=["< 50%", "50–70%", "70–85%", "85–95%", "95%+"])
            st.bar_chart(cal.groupby("Confidence", observed=True)["Correct"].mean(), height=300, sort=False,
                         x_label="Jev's confidence", y_label="Correct")

    wrong = lab[~lab["ok_category"] | ~lab["ok_action"]]  # Wrong type or next step
    with st.expander(f"Mistakes ({len(wrong)} emails with a wrong type or next step)"):
        st.dataframe(pd.DataFrame({
            "Subject": wrong["subject"],
            "Correct type": wrong["gold_category"].map(CATEGORY_LABEL),
            "Jev's type": wrong["answers"].map(lambda a: CATEGORY_LABEL[a["category"]]),
            "Correct step": wrong["gold_action"].map(ACTION_LABEL),
            "Jev's step": wrong["answers"].map(lambda a: ACTION_LABEL[a["action"]]),
            "Confidence": wrong["confidence"].map(lambda c: (c or {}).get("category")),
            "Hard email": wrong["tags"].fillna("").map(lambda t: ", ".join(x for x in t.split(",") if x in HARD)),
        }), hide_index=True, width="stretch",
            column_config={"Confidence": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
