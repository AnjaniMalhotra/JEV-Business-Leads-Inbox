"""One toolbar row: search, priority, Filters menu (and sort, on the Inbox). Shared by Inbox and Dashboard."""
import pandas as pd
import streamlit as st

from ui.labels import ACTION_LABEL, CATEGORY_LABEL, GRADE, PRIORITY, ROUTE_LABEL

SORTS = ["Priority first", "Best leads first", "Newest first"]  # Sort options for the Inbox


def filters(df: pd.DataFrame, key: str, inbox: bool = False) -> pd.DataFrame:
    """Render the toolbar and return the filtered (and, on the Inbox, sorted) emails."""
    ss = st.session_state
    extra = [ss.get(f"{key}_{k}") for k in ("grades", "types", "actions", "routes", "reply", "unsure", "new")]
    # Number shown on the Filters button
    active = sum(bool(v) for v in extra) + (ss.get(f"{key}_when", "Any time") != "Any time")

    cols = st.columns([3, 3.4, 1.2, 1.5] if inbox else [3, 3.6, 1.2], vertical_alignment="center")
    query = cols[0].text_input("Search", placeholder="Search sender, subject or text", key=f"{key}_q",
                               label_visibility="collapsed")
    prio = cols[1].segmented_control("Priority", list(PRIORITY), selection_mode="multi", key=f"{key}_prio",
                                     format_func=lambda b: PRIORITY[b][0], label_visibility="collapsed")
    with cols[2].popover(f"Filters{f' ({active})' if active else ''}", icon=":material/filter_list:", width="stretch"):
        grades = st.multiselect("Lead grade", list(GRADE), key=f"{key}_grades", format_func=lambda g: GRADE[g][0])
        types = st.multiselect("Type", list(CATEGORY_LABEL), key=f"{key}_types", format_func=CATEGORY_LABEL.get)
        actions = st.multiselect("Next step", list(ACTION_LABEL), key=f"{key}_actions", format_func=ACTION_LABEL.get)
        routes = st.multiselect("Owner", list(ROUTE_LABEL), key=f"{key}_routes", format_func=ROUTE_LABEL.get)
        when = st.selectbox("Received", ["Any time", "Last day", "Last 7 days", "Last 30 days"], key=f"{key}_when")
        reply = st.toggle("Waiting for my reply", key=f"{key}_reply")
        unsure = st.toggle("Needs review", key=f"{key}_unsure")
        new = st.toggle("Not sorted yet", key=f"{key}_new") if inbox else False
    order = cols[3].selectbox("Sort", SORTS, key=f"{key}_sort", label_visibility="collapsed") if inbox else None

    view = df  # Apply each filter in turn
    if query:
        q = query.lower()
        view = view[view[["name", "sender", "subject", "body"]].apply(lambda r: q in " ".join(map(str, r)).lower(), axis=1)]
    if prio:
        view = view[view["bucket"].isin(prio)]
    for col, chosen in (("lead_grade", grades), ("category", types), ("action", actions), ("route_to", routes)):
        if chosen:
            view = view[view[col].isin(chosen)]
    if when != "Any time" and len(view):  # Relative to the newest email
        days = {"Last day": 1, "Last 7 days": 7, "Last 30 days": 30}[when]
        stamps = pd.to_datetime(view["received_at"], utc=True, format="mixed")
        view = view[stamps >= pd.to_datetime(df["received_at"], utc=True, format="mixed").max() - pd.Timedelta(days=days)]
    if reply:
        view = view[view["needs_reply"].fillna(0).astype(float) >= 0.5]
    if unsure:
        view = view[view["needs_review"].fillna(False).astype(bool)]
    if new:
        view = view[~view["sorted"]]
    if order == "Best leads first":
        return view.assign(_s=view["lead_score"].astype(float)).sort_values("_s", ascending=False, na_position="last").drop(columns="_s")
    if order == "Newest first":
        return view.sort_values("received_at", ascending=False)
    if order == "Priority first":
        return view.sort_values(["sorted", "bucket", "priority", "received_at"], ascending=[False, True, False, False])
    return view
