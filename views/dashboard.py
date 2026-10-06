import pandas as pd
import streamlit as st

from ui.accuracy import show_accuracy
from ui.data import setup, triaged_inbox
from ui.filters import filters
from ui.labels import CATEGORY_LABEL, GRADE, PRIORITY, ROUTE_LABEL, money

setup()
st.header("Dashboard")
df = triaged_inbox()
if df.empty:
    st.info("Nothing sorted yet. Go to **Inbox** and click **Run Jev**.")
    st.stop()
df = filters(df, "dash")  # Same filters as the Inbox
if df.empty:
    st.info("No emails match these filters.")
    st.stop()

overview, accuracy = st.tabs(["Overview", "Accuracy"])
with overview:
    ai = df[df["source"] == "jev"]
    leads = df[df["lead_grade"].notna()]
    # Top row of numbers
    kpis = [("Emails", len(df)), ("Leads", len(leads)), ("Hot leads", int((leads["lead_grade"] == "A").sum())),
            ("Awaiting reply", int((df["needs_reply"].astype(float) >= 0.5).sum())),
            ("Need review", int(df["needs_review"].astype(bool).sum())),
            ("Jev cost / 1K emails", money(ai["cost_usd"].mean() * 1000) if len(ai) else "–")]
    for col, (label, value) in zip(st.columns(6), kpis):
        col.metric(label, value)

    def counts(col: str, labels: dict) -> pd.Series:  # Count per label, in label order
        return df[col].map(labels).value_counts().reindex(list(labels.values()), fill_value=0)

    def card(col, title: str, data, height: int = 240, **kw) -> None:  # A bordered chart with a title
        with col.container(border=True):
            st.markdown(f"**{title}**")
            st.bar_chart(data, height=height, x_label="", y_label="", **kw)

    priority_names = {b: name for b, (name, _) in PRIORITY.items()}
    # Emails per day, split by priority
    per_day = (df.assign(Day=pd.to_datetime(df["received_at"], utc=True, format="mixed").dt.date,
                         Priority=df["bucket"].map(priority_names))
               .pivot_table(index="Day", columns="Priority", values="id", aggfunc="count", fill_value=0)
               .reindex(columns=list(priority_names.values()), fill_value=0))
    per_day.index = pd.to_datetime(per_day.index).strftime("%d %b")  # labels in date order, not a time axis
    left, right = st.columns(2)
    card(left, "By type", counts("category", CATEGORY_LABEL).sort_values(ascending=False), horizontal=True, sort=False,
         height=30 * len(CATEGORY_LABEL) + 40)  # tall enough to label every type
    card(right, "Leads by grade", counts("lead_grade", {g: name for g, (name, _) in GRADE.items()}), horizontal=True,
         sort=False, color="#B45309", height=30 * len(CATEGORY_LABEL) + 40)  # amber next to teal
    left, right = st.columns(2)
    card(left, "By team", counts("route_to", ROUTE_LABEL).sort_values(ascending=False), horizontal=True, sort=False)
    card(right, "Emails per day", per_day, sort=False, color=["#B91C1C", "#D97706", "#0F766E", "#94A3B8"])
    from_gmail, fetched = int(df["gmail_id"].notna().sum()), st.session_state.get("last_fetch")
    gmail_note = f"{from_gmail} emails from Gmail{f', last fetched {fetched}' if fetched else ''}. " if from_gmail else ""
    st.caption(f"{gmail_note}You reviewed {int(df['reviewed'].astype(bool).sum())} emails and corrected "
               f"{int(df['corrected'].sum())}. Corrections are stored separately; Jev's own answers are never changed.")

with accuracy:
    show_accuracy(df)
