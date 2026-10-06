"""Stored model comparisons: one row per (model, email) in each run."""
import json

import pandas as pd

from db.store import connect, now, parse_json


def save_benchmark(run_id: str, mode: str, email_id: int, result: dict) -> None:  # One row per (model, email) in a run
    with connect() as conn:
        conn.execute(
            """INSERT INTO benchmark_runs (run_id, mode, model, email_id, answers_json, confidence_json,
               input_tokens, output_tokens, cost_usd, latency_ms, parse_error, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, mode, result.get("model"), email_id,
                json.dumps(result["answers"]) if result.get("answers") else None,
                json.dumps(result.get("confidence", {})), result.get("input_tokens"),
                result.get("output_tokens"), result.get("cost_usd"), result.get("latency_ms"),
                int(bool(result.get("parse_error"))), result.get("error"), now(),
            ),
        )


def benchmark_runs() -> pd.DataFrame:  # Runs, newest first
    with connect() as conn:
        return pd.read_sql(
            """SELECT run_id, MIN(created_at) AS started, COUNT(DISTINCT email_id) AS emails
               FROM benchmark_runs GROUP BY run_id ORDER BY started DESC""",
            conn,
        )


def benchmark_df(run_id: str) -> pd.DataFrame:  # All rows of one run
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM benchmark_runs WHERE run_id = ?", conn, params=(run_id,))
    df["answers"] = df["answers_json"].map(parse_json)
    df["confidence"] = df["confidence_json"].map(lambda v: parse_json(v, {}))
    return df
