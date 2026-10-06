"""Score stored answers against the correct ones: accuracy, precision / recall / F1, speed, cost."""
import pandas as pd

from db import benchmarks, store
from triage.schema import EVAL_FIELDS, SCORE_FIELDS


def field_correct(field: str, answer, gold) -> bool:  # Is one answer right? (0-3 scores are rounded)
    if answer is None or gold is None or pd.isna(gold):
        return False
    if field in SCORE_FIELDS:
        return round(float(answer)) == int(gold)
    if field == "needs_reply":
        return (float(answer) >= 0.5) == bool(gold)
    return answer == gold


def score_rows(df: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    """Add one `ok_<field>` column per eval field, and `labelled` (a correct answer is known)."""
    df = df.merge(gold, left_on="email_id", right_on="id", how="left")
    df["labelled"] = df["gold_category"].notna()  # Only emails with a known answer count
    for f in EVAL_FIELDS:
        df[f"ok_{f}"] = [field_correct(f, (a or {}).get(f), g) for a, g in zip(df["answers"], df[f"gold_{f}"])]
    return df


def macro_prf(pred: pd.Series, gold: pd.Series) -> tuple[float, float, float]:
    """Macro-averaged precision, recall and F1 over the email types (a failed answer counts as wrong)."""
    ps, rs, fs = [], [], []
    for c in sorted(set(gold)):
        tp = int(((pred == c) & (gold == c)).sum())  # True positives for this type
        fp = int(((pred == c) & (gold != c)).sum())
        fn = int(((pred != c) & (gold == c)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        ps.append(p)
        rs.append(r)
        fs.append(2 * p * r / (p + r) if p + r else 0.0)
    n = max(len(ps), 1)
    return sum(ps) / n, sum(rs) / n, sum(fs) / n


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    """One row per model: speed, cost, accuracy, precision/recall/F1, failures."""
    rows = []
    ok_cols = [f"ok_{f}" for f in EVAL_FIELDS]
    for mode, g in scored.groupby("mode", sort=False):
        lab = g[g["labelled"]]  # accuracy only where we know the right answer
        pred = lab["answers"].map(lambda a: (a or {}).get("category"))
        # Quality on the email type question
        precision, recall, f1 = macro_prf(pred, lab["gold_category"]) if len(lab) else (float("nan"),) * 3
        row = {
            "mode": mode,
            "model": g["model"].dropna().iloc[0] if g["model"].notna().any() else mode,
            "emails": len(g),
            "labelled": len(lab),
            "total_cost_usd": g["cost_usd"].sum(),
            "cost_per_email_usd": g["cost_usd"].mean(),
            "avg_latency_ms": g["latency_ms"].mean(),
            "p50_latency_ms": g["latency_ms"].median(),
            "p95_latency_ms": g["latency_ms"].quantile(0.95),
            "total_latency_ms": g["latency_ms"].sum(),
            "errors": int(g["parse_error"].astype(bool).sum()),
            "accuracy_avg": lab[ok_cols].to_numpy().mean() if len(lab) else float("nan"),
            "precision": precision, "recall": recall, "f1": f1,
        }
        for f in EVAL_FIELDS:
            row[f"acc_{f}"] = lab[f"ok_{f}"].mean() if len(lab) else float("nan")
        if "escalated" in g:
            row["escalated_pct"] = g["escalated"].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def load_scored(run_id: str) -> pd.DataFrame:  # A stored run, scored against the answer key
    gold = store.emails_df()[["id"] + [f"gold_{f}" for f in EVAL_FIELDS] + ["tags"]]
    return score_rows(benchmarks.benchmark_df(run_id), gold)
