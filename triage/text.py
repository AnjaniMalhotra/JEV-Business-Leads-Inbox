"""Email text cleanup before anything reaches a model."""
import html
import re

_TAG = re.compile(r"<[^>]+>")  # Any HTML tag
_SPACE = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")


def clean_body(body: str, max_chars: int) -> str:  # HTML to plain text, capped length
    text = _TAG.sub(" ", body or "")
    text = html.unescape(text).replace("\xa0", " ")
    text = _SPACE.sub(" ", text)
    text = _BLANKS.sub("\n\n", text).strip()
    return text[:max_chars]


def estimate_tokens(text: str) -> int:  # Roughly 4 characters per token
    """Rough fallback when a provider does not report usage (~4 chars/token)."""
    return max(1, len(text) // 4)
