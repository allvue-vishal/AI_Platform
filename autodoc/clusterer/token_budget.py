"""Token counting and budget management for LLM context windows."""

from __future__ import annotations

import tiktoken

_ENCODER: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _ENCODER
    if _ENCODER is None:
        try:
            _ENCODER = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def count_tokens(text: str) -> int:
    """Count tokens in a string using the cl100k_base encoding."""
    return len(_get_encoder().encode(text))


def fits_in_budget(text: str, max_tokens: int) -> bool:
    """Check if text fits within the token budget."""
    return count_tokens(text) <= max_tokens


def truncate_to_budget(text: str, max_tokens: int, suffix: str = "\n... (truncated)") -> str:
    """Truncate text to fit within token budget."""
    enc = _get_encoder()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    suffix_tokens = enc.encode(suffix)
    allowed = max_tokens - len(suffix_tokens)
    return enc.decode(tokens[:allowed]) + suffix
