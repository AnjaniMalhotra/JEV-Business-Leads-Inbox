"""App settings, the LLM model list, and helpers for the API keys entered in the sidebar.

`keys` is a plain dict built by the sidebar:
    {"jev": str, "provider": str, "model": str, "llm_key": str, "price_in": float, "price_out": float, "name": str}
A missing key means that provider runs in demo mode (practice answers).
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent  # Project folder

JEV_MODEL = "jev-1.13.0"  # pinned: newer versions can change answers
JEV_PRICE = 0.042  # USD per 1M input tokens; Jev's output is free

# provider -> model -> (USD per 1M input tokens, per 1M output tokens)
MODELS = {
    "Gemini": {"gemini-3.8-flash": (0.75, 3.75), "gemini-3.5-flash-lite": (0.30, 2.50), "gemini-3.1-pro-preview": (2.00, 12.00)},
    "OpenAI": {"gpt-5.6-luna": (0.20, 1.20), "gpt-5.6-terra": (2.00, 12.00), "gpt-6-astra": (10.00, 50.00)},
    "Claude": {"claude-opus-5": (5.00, 25.00), "claude-sonnet-5": (2.00, 10.00), "claude-haiku-4-5": (1.00, 5.00)},
}


def jev_is_mock(keys: dict) -> bool:  # No Jev key: demo answers
    return not keys.get("jev")


def llm_is_mock(keys: dict) -> bool:  # No LLM key or model: demo answers
    return not (keys.get("llm_key") and keys.get("model"))


_db_resolver = None  # set by the UI so every visitor gets their own database


def set_db_resolver(resolver) -> None:
    global _db_resolver
    _db_resolver = resolver


def db_path() -> Path:  # Per-visitor file when the UI provides one; tests point DB_PATH at a temp file
    return (_db_resolver and _db_resolver()) or ROOT / os.getenv("DB_PATH", "data/inbox.db")


@lru_cache  # Read config/app.yaml only once
def app_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "app.yaml").read_text())
