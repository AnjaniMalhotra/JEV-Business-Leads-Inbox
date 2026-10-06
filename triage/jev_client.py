"""Jev (TypeSafe AI) — one call answers every triage question in parallel."""
import json
import time

from triage import mock
from triage.config import JEV_MODEL, JEV_PRICE, app_config, jev_is_mock
from triage.schema import QUESTIONS, Question, email_state
from triage.text import estimate_tokens


def _to_sdk(q: Question):  # Our Question -> the SDK's Choice / Score / Noul
    from typesafe_sdk import Choice, Noul, Score

    if q.kind == "choice":
        return Choice(instructions=q.instructions, criteria=q.options)
    if q.kind == "score":
        return Score(instructions=q.instructions, criteria=q.levels)
    return Noul(instructions=q.instructions)


def _parse(response) -> dict:  # SDK response -> plain dicts
    answers, probabilities, confidence = {}, {}, {}
    for key, ans in response.answers.items():
        if ans.type == "choice":  # Choice: the picked option, its probabilities and confidence
            answers[key] = ans.choice
            probabilities[key] = dict(ans.probabilities)
            confidence[key] = ans.confidence
        elif ans.type == "score":
            answers[key] = ans.score  # 0-based, may fall between levels
            probabilities[key] = {str(k): v for k, v in ans.probabilities.items()}
            confidence[key] = ans.confidence
        else:
            answers[key] = ans.noul  # Noul: probability the statement is true
    return {"answers": answers, "probabilities": probabilities, "confidence": confidence}


def classify(email: dict, keys: dict) -> dict:  # Ask Jev every question about one email
    """Triage one (already cleaned) email. Returns answers + usage + cost + latency."""
    state = email_state(email, app_config()["max_body_chars"])

    if jev_is_mock(keys):  # No key: practice answers
        result = mock.jev_like(email)
        result["model"] = "mock-jev"
    else:
        from typesafe_sdk import TypeSafeClient

        questions = {q.key: _to_sdk(q) for q in QUESTIONS}  # All questions go in one call (fan-out)
        start = time.perf_counter()
        client = TypeSafeClient(api_key=keys["jev"], model=JEV_MODEL, timeout=30)  # Pinned model version
        response = client.system_one(state=state, questions=questions)  # The single Jev call
        result = _parse(response)
        result["latency_ms"] = (time.perf_counter() - start) * 1000
        result["model"] = response.model
        result["input_tokens"] = response.usage.input_tokens
        result["output_tokens"] = response.usage.output_tokens or 0

    if not result.get("input_tokens"):
        prompt = json.dumps(state) + json.dumps([q.__dict__ for q in QUESTIONS])
        result["input_tokens"] = estimate_tokens(prompt)
    result["cost_usd"] = result["input_tokens"] / 1e6 * JEV_PRICE  # Jev bills input tokens only
    result["provider"] = "jev"
    return result
