"""Compare models: the same emails through Jev and any LLMs, side by side."""
import pandas as pd
import streamlit as st

from db import benchmarks, store
from triage import benchmark, scoring
from ui.data import setup
from ui.labels import money, pct
from ui.sidebar import keys, llm_specs, session_config

setup()
st.header("Compare models")
st.caption("The same emails and the same 8 questions, answered by Jev and by the LLMs you choose.")

specs = {s["name"]: s for s in llm_specs()}  # Every LLM you can compare with
default = [keys().get("name")] if keys().get("name") in specs else list(specs)[:1]
total = len(store.emails_df())

if total < 2:
    st.info("Load at least 2 emails to compare models.")
    st.stop()
c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
n = c1.slider("Number of emails", 1, total, min(20, total))
chosen = c2.multiselect("Compare Jev with", list(specs), default=default,
                        format_func=lambda s: s + ("" if specs[s]["llm_key"] else " (demo)"))
with st.expander("Advanced"):
    conc = st.slider("Requests at the same time", 1, 16, 8)
    threshold = session_config()["review_confidence"]
    st.caption(f"Smart combo: Jev answers everything; emails where Jev is under {threshold:.0%} confident "
               "(the review setting in the sidebar) go to the first LLM instead.")

# Run all models and store the results
if st.button(f"Compare on {n} emails", type="primary", icon=":material/play_arrow:", disabled=not chosen):
    bar = st.progress(0.0, text="Starting…")
    benchmark.run(store.emails_df().head(n).to_dict("records"), keys(), [specs[s] for s in chosen],
                  concurrency=conc, on_progress=lambda d, t: bar.progress(d / t, f"{d} of {t} answers"))
    st.rerun()

runs = benchmarks.benchmark_runs()  # Newest run is shown by default
if runs.empty:
    st.info("No comparison yet. Choose models and press **Compare**.")
    st.stop()

run_id = st.selectbox("Showing", runs["run_id"], key=f"compare_run_{runs['run_id'].iloc[0]}",  # newest run first
                      format_func=lambda r: f"Run {r} · {int(runs.set_index('run_id').loc[r, 'emails'])} emails")
scored = scoring.load_scored(run_id)
modes = [m for m in scored["mode"].unique() if m != "jev"]
parts = [scored]
if modes:
    parts.append(benchmark.cascade(scored, threshold, modes[0]))  # Add the Smart combo column
summary = scoring.summarize(pd.concat(parts)).set_index("mode")
order = ["jev", *modes, *([benchmark.COMBO] if modes else [])]
summary = summary.loc[order]
name = {"jev": "Jev", "llm": str(summary.loc["llm", "model"]) if "llm" in summary.index else "LLM"}
label = {m: name.get(m, m) + (" (demo)" if str(summary.loc[m, "model"]).startswith("mock") else "") for m in order}

if any("(demo)" in v for v in label.values()):
    st.warning("Some models ran in demo mode (no key), so their numbers are simulated.")

jev = summary.loc["jev"]
if modes:
    lines = []
    for m in modes:
        s = summary.loc[m]
        diff = "" if pd.isna(s.accuracy_avg) else f", accuracy {(jev.accuracy_avg - s.accuracy_avg) * 100:+.0f} pts"
        lines.append(f"**{s.avg_latency_ms / max(jev.avg_latency_ms, 1e-9):.0f}× faster** and "
                     f"**{s.cost_per_email_usd / max(jev.cost_per_email_usd, 1e-12):,.0f}× cheaper** than {label[m]}{diff}")
    st.success("Jev was " + "; ".join(lines) + ".")

rows = {  # Table rows: label -> how to format it
    "Avg. response time": lambda s: f"{s.avg_latency_ms / 1000:.2f}s",
    "Slowest 5%": lambda s: f"{s.p95_latency_ms / 1000:.2f}s",
    "Cost for this run": lambda s: money(s.total_cost_usd),
    "Cost per 1K emails": lambda s: money(s.cost_per_email_usd * 1000),
    "Cost per 1M emails": lambda s: money(s.cost_per_email_usd * 1e6),
    "Accuracy (all questions)": lambda s: pct(s.accuracy_avg),
    "Precision (type)": lambda s: pct(s.precision),
    "Recall (type)": lambda s: pct(s.recall),
    "F1 (type)": lambda s: pct(s.f1),
    "Failed answers": lambda s: str(int(s.errors)),
}
table = pd.DataFrame({label[m]: [fmt(summary.loc[m]) for fmt in rows.values()] for m in order}, index=list(rows))
st.dataframe(table, width="stretch", height=36 * len(table) + 40)
st.caption(f"Accuracy on {int(jev.labelled)} emails with a known answer; precision, recall and F1 are averaged over "
           "the 7 email types. The Smart combo pays for both models on emails it passes to the LLM"
           + (f" ({pct(summary.loc[benchmark.COMBO, 'escalated_pct'])} of them)." if modes else "."))

left, right = st.columns(2)
for col, title, values in ((left, "Cost per 1K emails ($)", summary["cost_per_email_usd"] * 1000),
                           (right, "Seconds per email", summary["avg_latency_ms"] / 1000)):
    with col.container(border=True):
        st.markdown(f"**{title}**")
        st.bar_chart(values.rename(index=label), horizontal=True, sort=False, height=200, x_label="", y_label="")

failed = scored[scored["parse_error"].astype(bool)]  # Calls that errored or returned bad JSON
if len(failed):
    with st.expander(f"Failed answers ({len(failed)})"):
        st.dataframe(failed[["mode", "email_id", "error"]], hide_index=True, width="stretch")
