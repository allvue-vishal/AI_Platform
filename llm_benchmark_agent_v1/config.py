"""
Global configuration for the LLM Benchmark Agent.
Values are loaded from .env / environment variables and can be overridden at
runtime via CLI arguments in main.py.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    """Mutable settings singleton."""

    LITELLM_PROXY_URL: str = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
    LITELLM_API_KEY: str = os.getenv("LITELLM_API_KEY", "")
    JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", "gpt-4o")
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", os.path.join("data", "results"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))

    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "")

    BENCHMARK_TEMPERATURE: float = 0.0
    BENCHMARK_MAX_TOKENS: int = 2048

    EMBEDDING_FILTER_KEYWORDS: list[str] = [
        "embed", "embedding", "text-embedding", "ada-002",
    ]


settings = _Settings()


CATEGORY_META = {
    "reasoning": {
        "name": "Reasoning",
        "description": "Logical deduction, syllogisms, incentive logic, return math traps",
    },
    "math": {
        "name": "Math",
        "description": "NPV, IRR, compound interest, WACC, bond pricing, mortgage calculations",
    },
    "coding": {
        "name": "Coding",
        "description": "Python code generation: returns, Sharpe ratio, amortization, CAGR",
    },
    "knowledge": {
        "name": "Knowledge",
        "description": "Factual questions: fund structures, regulations, valuation concepts",
    },
    "summarization": {
        "name": "Summarization",
        "description": "Summarizing earnings calls, 10-K filings, fund letters, FOMC statements",
    },
    "classification": {
        "name": "Classification",
        "description": "Sentiment analysis, document type, news categorization, fraud detection",
    },
    "tool_use": {
        "name": "Tool Use",
        "description": "Function calling: stock quotes, risk metrics, filings, fund screening",
    },
    "conversation": {
        "name": "Conversation",
        "description": "Multi-turn dialogue: portfolio advice, due diligence, risk discussions",
    },
    "analysis": {
        "name": "Analysis",
        "description": "DCF valuation, LBO modeling, ratio analysis, deal structuring",
    },
    "compliance": {
        "name": "Compliance",
        "description": "SEC rules, fund regulations, AML/KYC, fiduciary duty, Dodd-Frank",
    },
}
