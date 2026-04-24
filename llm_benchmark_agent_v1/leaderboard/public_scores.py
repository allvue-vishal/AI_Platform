"""Fetch public benchmark scores from the Hugging Face Open LLM Leaderboard.

Uses the HF Datasets API to pull results and returns a normalised DataFrame
that the Streamlit UI can merge with local benchmark results.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

HF_LEADERBOARD_API = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=open-llm-leaderboard/results"
    "&config=default"
    "&split=train"
    "&offset=0"
    "&length=100"
)

MODEL_ALIAS_MAP: dict[str, list[str]] = {
    "gpt-4o": ["gpt-4o", "openai/gpt-4o"],
    "gpt-4": ["gpt-4", "openai/gpt-4"],
    "gpt-3.5-turbo": ["gpt-3.5-turbo", "openai/gpt-3.5-turbo"],
    "claude-sonnet-4-5": ["claude-3.5-sonnet", "anthropic/claude-3.5-sonnet", "claude-sonnet-4-5"],
    "claude-sonnet-4": ["claude-3-sonnet", "anthropic/claude-3-sonnet", "claude-sonnet-4"],
    "claude-haiku-4-5": ["claude-3-haiku", "anthropic/claude-3-haiku", "claude-haiku-4-5"],
    "llama-3-70b": ["meta-llama/Meta-Llama-3-70B-Instruct", "llama-3-70b"],
    "llama-3-8b": ["meta-llama/Meta-Llama-3-8B-Instruct", "llama-3-8b"],
    "mistral-large": ["mistralai/Mistral-Large-Instruct", "mistral-large"],
    "gemini-pro": ["google/gemini-pro", "gemini-pro"],
}

PUBLIC_BENCHMARK_COLS = [
    "model_name",
    "MMLU",
    "ARC",
    "HellaSwag",
    "TruthfulQA",
    "Winogrande",
    "GSM8K",
    "average",
]

KNOWN_PUBLIC_SCORES: list[dict[str, Any]] = [
    {"model_name": "gpt-4o", "MMLU": 88.7, "ARC": 96.3, "HellaSwag": 95.3, "TruthfulQA": 64.1, "Winogrande": 87.5, "GSM8K": 95.8, "average": 87.9},
    {"model_name": "gpt-4", "MMLU": 86.4, "ARC": 96.3, "HellaSwag": 95.3, "TruthfulQA": 59.0, "Winogrande": 87.5, "GSM8K": 92.0, "average": 86.1},
    {"model_name": "claude-sonnet-4-5", "MMLU": 88.3, "ARC": 96.4, "HellaSwag": 89.0, "TruthfulQA": 67.2, "Winogrande": 85.4, "GSM8K": 92.3, "average": 86.4},
    {"model_name": "claude-sonnet-4", "MMLU": 79.0, "ARC": 93.2, "HellaSwag": 85.9, "TruthfulQA": 62.1, "Winogrande": 82.1, "GSM8K": 73.5, "average": 79.3},
    {"model_name": "claude-haiku-4-5", "MMLU": 75.2, "ARC": 89.2, "HellaSwag": 82.6, "TruthfulQA": 58.3, "Winogrande": 78.4, "GSM8K": 66.5, "average": 75.0},
    {"model_name": "llama-3-70b", "MMLU": 82.0, "ARC": 93.0, "HellaSwag": 87.3, "TruthfulQA": 61.8, "Winogrande": 85.3, "GSM8K": 93.0, "average": 83.7},
    {"model_name": "llama-3-8b", "MMLU": 68.4, "ARC": 80.6, "HellaSwag": 78.6, "TruthfulQA": 51.7, "Winogrande": 77.4, "GSM8K": 79.6, "average": 72.7},
    {"model_name": "mistral-large", "MMLU": 81.2, "ARC": 94.0, "HellaSwag": 86.7, "TruthfulQA": 50.6, "Winogrande": 83.6, "GSM8K": 91.2, "average": 81.2},
]


@lru_cache(maxsize=1)
def fetch_hf_leaderboard() -> pd.DataFrame:
    """Try to fetch live data from HF Open LLM Leaderboard.

    Falls back to KNOWN_PUBLIC_SCORES if the API is unreachable.
    """
    try:
        resp = requests.get(HF_LEADERBOARD_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("rows", [])
        if rows:
            records = [r.get("row", {}) for r in rows]
            df = pd.DataFrame(records)
            df = _normalise_hf_df(df)
            if not df.empty:
                return df
    except Exception as exc:
        logger.warning("Could not fetch HF leaderboard, using fallback: %s", exc)

    return pd.DataFrame(KNOWN_PUBLIC_SCORES)


def _normalise_hf_df(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw HF leaderboard columns to our standard format."""
    col_map = {}
    for col in df.columns:
        low = col.lower()
        if "model" in low and "name" in low:
            col_map[col] = "model_name"
        elif "mmlu" in low:
            col_map[col] = "MMLU"
        elif "arc" in low:
            col_map[col] = "ARC"
        elif "hellaswag" in low:
            col_map[col] = "HellaSwag"
        elif "truthfulqa" in low:
            col_map[col] = "TruthfulQA"
        elif "winogrande" in low:
            col_map[col] = "Winogrande"
        elif "gsm" in low:
            col_map[col] = "GSM8K"
        elif "average" in low:
            col_map[col] = "average"

    if "model_name" not in col_map.values():
        return pd.DataFrame()

    df = df.rename(columns=col_map)
    available = [c for c in PUBLIC_BENCHMARK_COLS if c in df.columns]
    return df[available].copy()


def match_model_to_public(local_model_id: str) -> str | None:
    """Attempt to match a local model ID to a public leaderboard model name."""
    local_lower = local_model_id.lower()
    for canonical, aliases in MODEL_ALIAS_MAP.items():
        for alias in aliases:
            if alias.lower() in local_lower or local_lower in alias.lower():
                return canonical
    return None


def get_comparison_df(local_results: list[dict]) -> pd.DataFrame:
    """Build a comparison DataFrame merging local and public scores.

    Args:
        local_results: List of dicts with keys 'model', 'category', 'avg_score'.

    Returns:
        DataFrame with both local custom scores and public benchmark scores.
    """
    public_df = fetch_hf_leaderboard()

    local_df = pd.DataFrame(local_results)
    if local_df.empty:
        return public_df

    pivot = local_df.pivot_table(
        index="model", columns="category", values="avg_score", aggfunc="mean"
    ).reset_index()
    pivot = pivot.rename(columns={"model": "model_name"})

    pivot["_public_name"] = pivot["model_name"].apply(match_model_to_public)

    merged = pivot.merge(
        public_df,
        left_on="_public_name",
        right_on="model_name",
        how="left",
        suffixes=("", "_public"),
    )

    if "model_name_public" in merged.columns:
        merged = merged.drop(columns=["model_name_public"])
    if "_public_name" in merged.columns:
        merged = merged.drop(columns=["_public_name"])

    return merged
