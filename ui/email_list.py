"""The email list: priority and label chips; click a row to open the email."""
import pandas as pd
import streamlit as st

from ui.labels import ACTION_LABEL, PRIORITY, TAG_COLOURS, short_date, tags

PRIO_OPTS = [name for name, _ in PRIORITY.values()] + ["New"]  # Chip options for the Priority column


def email_list(view: pd.DataFrame) -> int | None:
    """Show the list; returns the id of the clicked email, if any."""
    table = pd.DataFrame({
        "id": view["id"],
        "Priority": [[PRIORITY[b][0]] if s else ["New"] for b, s in zip(view["bucket"], view["sorted"])],
        "From": view["name"],
        "Email": [("📎 " if n else "") + f"{s} — {b[:90]}" for s, b, n in zip(view["subject"], view["body"], view["n_attachments"])],
        "Labels": [[t for t, _ in tags(r)] if r["sorted"] else [] for _, r in view.iterrows()],
        "Next step": [ACTION_LABEL.get(a, "") if s else "" for a, s in zip(view["action"], view["sorted"])],
        "Date": view["received_at"].map(short_date),
    })
    event = st.dataframe(  # Clickable table: a click selects a row
        table, hide_index=True, width="stretch", height=min(36 * len(table) + 40, 640),
        on_select="rerun", selection_mode="single-row", key=f"inbox_list_{st.session_state.get('list_version', 0)}",
        column_order=["Priority", "From", "Email", "Labels", "Next step", "Date"],
        column_config={
            "Priority": st.column_config.MultiselectColumn(options=PRIO_OPTS, width=100,
                                                          color=[c for _, c in PRIORITY.values()] + ["violet"]),
            "From": st.column_config.TextColumn(width=120),
            "Email": st.column_config.TextColumn(width=270),
            "Labels": st.column_config.MultiselectColumn(options=list(TAG_COLOURS), color=list(TAG_COLOURS.values()), width=270),
            "Next step": st.column_config.TextColumn(width=110),
            "Date": st.column_config.TextColumn(width=60),
        },
    )
    return int(table.iloc[event.selection.rows[0]]["id"]) if event.selection.rows else None
