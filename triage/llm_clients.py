"""SDK clients for Gemini, OpenAI and Claude: one per provider + key, with a time limit and at most one retry."""
from functools import lru_cache

TIMEOUT_S = 60  # give up after a minute instead of spinning forever (e.g. retrying an exhausted free quota)


@lru_cache(maxsize=8)  # Reuse one client per provider
def client(provider: str, key: str):
    """One client per provider+key, reused (an inline client gets garbage-collected mid-request). One retry at most."""
    if provider == "Gemini":
        from google import genai
        from google.genai import types

        retry = types.HttpRetryOptions(attempts=2)
        return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_S * 1000, retry_options=retry))
    if provider == "OpenAI":
        from openai import OpenAI

        return OpenAI(api_key=key, timeout=TIMEOUT_S, max_retries=1)
    import anthropic

    return anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=1)
