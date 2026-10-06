"""Run Jev and one or more LLMs on the same emails, and build the Smart combo.

A run stores one row per (model, email). The Smart combo is derived from stored rows (no extra
API calls): Jev answers every email; where Jev's category/action confidence is below a threshold,
the LLM's answer is used instead, and both calls are paid for."""
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd

from db import benchmarks
from triage import jev_client, llm_baseline
from triage.pipeline import prepare
from triage.schema import EVAL_FIELDS


COMBO = "Smart combo"  # Name of the Jev + LLM rows


def _safe_call(spec: dict | None, email: dict, keys: dict) -> dict:  # One model call that never crashes the run
    try:
        return jev_client.classify(email, keys) if spec is None else llm_baseline.classify(email, spec)
    except Exception as exc:  # an API failure counts as a failed answer, not a crash
        return {
            "answers": None, "confidence": {}, "parse_error": True,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_ms": None,
            "model": (spec or {}).get("model") or "jev",
        }


def run(  # Ask Jev and every chosen LLM about the same emails
    emails: list[dict],
    keys: dict,
    llms: list[dict] | None = None,
    concurrency: int = 4,
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """Jev plus every LLM in `llms` (each a keys-style dict with provider/model/llm_key/prices/name)."""
    llms = [keys] if llms is None else llms
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    jobs = [("jev", None, prepare(e)) for e in emails]  # One job per (model, email)
    jobs += [(spec.get("name") or "llm", spec, prepare(e)) for spec in llms for e in emails]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:  # Several requests at once
        futures = {pool.submit(_safe_call, spec, e, keys): (mode, e) for mode, spec, e in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            mode, email = futures[future]
            benchmarks.save_benchmark(run_id, mode, email["id"], future.result())  # Store each answer as it arrives
            if on_progress:
                on_progress(done, len(jobs))
    return run_id


# Smart combo: Jev first, the LLM only when Jev is unsure
def cascade(scored: pd.DataFrame, threshold: float, llm_mode: str | None = None) -> pd.DataFrame:
    """Smart combo rows: Jev's answer, or the LLM's where Jev was unsure (or failed)."""
    llm_mode = llm_mode or next(m for m in scored["mode"].unique() if m != "jev")
    jev = scored[scored["mode"] == "jev"].set_index("email_id")
    llm = scored[scored["mode"] == llm_mode].set_index("email_id")
    common = jev.index.intersection(llm.index)
    jev, llm = jev.loc[common], llm.loc[common]

    def low(conf: dict) -> bool:
        return any((conf or {}).get(k, 1.0) < threshold for k in ("category", "action"))

    escalate = jev["confidence"].map(low) | jev["answers"].isna()  # Emails Jev was unsure about (or failed)
    out = jev.copy()
    for col in ["answers", "parse_error"] + [f"ok_{f}" for f in EVAL_FIELDS]:
        out[col] = llm[col].where(escalate, jev[col])
    for col in ("cost_usd", "latency_ms", "input_tokens", "output_tokens"):
        out[col] = jev[col] + llm[col].where(escalate, 0)  # Combo pays for both calls on escalated emails
    out["escalated"] = escalate
    out["mode"] = COMBO
    out["model"] = f"jev + {llm['model'].iloc[0] if len(llm) else llm_mode}"
    return out.reset_index()
