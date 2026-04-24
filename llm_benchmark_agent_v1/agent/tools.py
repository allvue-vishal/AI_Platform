"""LangChain tools for the benchmarking agent."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime

from langchain_core.tools import tool

from config import settings
from models.discovery import list_models, list_model_ids
from benchmarks.registry import (
    ALL_BENCHMARKS,
    get_benchmark_by_category,
    get_all_categories,
    CATEGORY_SLUG_MAP,
)
from benchmarks.base import BenchmarkResult
from evaluation.scorer import run_benchmark_for_model


_results_store: list[BenchmarkResult] = []


def get_results_store() -> list[BenchmarkResult]:
    return _results_store


def clear_results_store():
    _results_store.clear()


@tool
def discover_models() -> str:
    """List all models available on the LiteLLM proxy with their metadata."""
    models = asyncio.run(list_models())
    if not models:
        return "No models found on the LiteLLM proxy. Check LITELLM_PROXY_URL and LITELLM_API_KEY."

    lines = [f"Found {len(models)} models on {settings.LITELLM_PROXY_URL}:\n"]
    for m in models:
        info_parts = [f"  - {m.id}"]
        if m.owned_by:
            info_parts.append(f"owned_by={m.owned_by}")
        if m.max_tokens:
            info_parts.append(f"max_tokens={m.max_tokens}")
        if m.supports_function_calling:
            info_parts.append("supports_tools=yes")
        lines.append(", ".join(info_parts))
    return "\n".join(lines)


@tool
def list_benchmark_categories() -> str:
    """List all available benchmark categories and their descriptions."""
    lines = ["Available benchmark categories:\n"]
    for b in ALL_BENCHMARKS:
        tasks = b.get_tasks()
        lines.append(f"  - {b.category}: {b.description} ({len(tasks)} tasks)")
    lines.append(f"\nCategory slugs for filtering: {', '.join(sorted(CATEGORY_SLUG_MAP.keys()))}")
    return "\n".join(lines)


@tool
def run_benchmark(model: str, category: str) -> str:
    """Run a specific benchmark category against a model. Returns scores and metrics.

    Args:
        model: The model ID to benchmark (e.g., 'gpt-4o', 'claude-sonnet').
        category: The benchmark category slug (e.g., 'code', 'math', 'reasoning').
    """
    benchmark = get_benchmark_by_category(category)
    if not benchmark:
        return f"Unknown category '{category}'. Use list_benchmark_categories to see available options."

    judge_model = settings.JUDGE_MODEL or None
    result = run_benchmark_for_model(benchmark, model, judge_model)
    _results_store.append(result)
    _save_result(result)

    lines = [
        f"\n=== {result.benchmark_name} — {result.model} ===",
        f"Average Score: {result.avg_score}/100",
        f"Average Latency: {result.avg_latency}s",
        f"Total Tokens: {result.total_tokens} (prompt: {result.total_prompt_tokens}, completion: {result.total_completion_tokens})",
        f"Estimated Cost: ${result.estimated_cost:.6f}",
        "\nTask Results:",
    ]
    for tr in result.task_results:
        status = "PASS" if tr.score >= 70 else ("PARTIAL" if tr.score >= 40 else "FAIL")
        err = f" [ERROR: {tr.error}]" if tr.error else ""
        lines.append(f"  {tr.task_id}: {tr.score:.0f}/100 ({status}) - {tr.latency_seconds}s{err}")

    return "\n".join(lines)


@tool
def run_all_benchmarks(models: str, categories: str = "") -> str:
    """Run benchmarks across multiple models and categories.

    Args:
        models: Comma-separated list of model IDs (e.g., 'gpt-4o,claude-sonnet').
        categories: Comma-separated category slugs. Empty string means all categories.
    """
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    if not model_list:
        return "No models specified."

    if categories.strip():
        cat_slugs = [c.strip() for c in categories.split(",") if c.strip()]
        benchmarks = []
        for slug in cat_slugs:
            b = get_benchmark_by_category(slug)
            if b:
                benchmarks.append(b)
        if not benchmarks:
            return f"No valid categories found in: {categories}"
    else:
        benchmarks = ALL_BENCHMARKS

    judge_model = settings.JUDGE_MODEL or None
    summary_lines = [f"Running {len(benchmarks)} benchmarks across {len(model_list)} models...\n"]

    for model in model_list:
        for benchmark in benchmarks:
            summary_lines.append(f">>> {benchmark.category} on {model}")
            result = run_benchmark_for_model(benchmark, model, judge_model)
            _results_store.append(result)
            _save_result(result)
            summary_lines.append(
                f"    Score: {result.avg_score}/100 | Latency: {result.avg_latency}s | Cost: ${result.estimated_cost:.6f}"
            )

    summary_lines.append("\nAll benchmarks complete. Use generate_report to create a detailed report.")
    return "\n".join(summary_lines)


@tool
def generate_report(format: str = "cli") -> str:
    """Generate a benchmark report from collected results.

    Args:
        format: Report format — 'cli' for terminal table, 'html' for web report, 'csv' for spreadsheet.
    """
    if not _results_store:
        return "No benchmark results available. Run some benchmarks first."

    if format == "cli":
        from reports.cli_report import generate_cli_report
        return generate_cli_report(_results_store)
    elif format == "html":
        from reports.html_report import generate_html_report
        path = generate_html_report(_results_store)
        return f"HTML report saved to: {path}"
    elif format == "csv":
        from reports.csv_report import generate_csv_report
        path = generate_csv_report(_results_store)
        return f"CSV report saved to: {path}"
    else:
        return f"Unknown format '{format}'. Use 'cli', 'html', or 'csv'."


@tool
def get_best_model_for(use_case: str) -> str:
    """Recommend the best model for a specific use case based on benchmark results.

    Args:
        use_case: The use case or category to find the best model for.
    """
    if not _results_store:
        return "No benchmark results available. Run benchmarks first to get recommendations."

    use_case_lower = use_case.lower()
    matching = [
        r for r in _results_store
        if use_case_lower in r.category.lower() or use_case_lower in r.benchmark_name.lower()
    ]

    if not matching:
        all_cats = set(r.category for r in _results_store)
        return (
            f"No results found for '{use_case}'. "
            f"Available categories with results: {', '.join(sorted(all_cats))}"
        )

    best = max(matching, key=lambda r: r.avg_score)
    alternatives = sorted(matching, key=lambda r: r.avg_score, reverse=True)

    lines = [f"\nBest model for '{use_case}': **{best.model}** (score: {best.avg_score}/100)\n"]
    if len(alternatives) > 1:
        lines.append("All models ranked:")
        for i, r in enumerate(alternatives, 1):
            lines.append(
                f"  {i}. {r.model}: {r.avg_score}/100 (latency: {r.avg_latency}s, cost: ${r.estimated_cost:.6f})"
            )

    return "\n".join(lines)


def _save_result(result: BenchmarkResult):
    """Persist result to JSON file."""
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = result.model.replace("/", "_").replace(":", "_")
    safe_cat = result.category.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}_{safe_cat}_{timestamp}.json"
    filepath = os.path.join(settings.RESULTS_DIR, filename)

    data = {
        "benchmark_name": result.benchmark_name,
        "category": result.category,
        "model": result.model,
        "avg_score": result.avg_score,
        "avg_latency": result.avg_latency,
        "total_prompt_tokens": result.total_prompt_tokens,
        "total_completion_tokens": result.total_completion_tokens,
        "total_tokens": result.total_tokens,
        "estimated_cost": result.estimated_cost,
        "timestamp": timestamp,
        "task_results": [
            {
                "task_id": tr.task_id,
                "score": tr.score,
                "latency_seconds": tr.latency_seconds,
                "prompt_tokens": tr.prompt_tokens,
                "completion_tokens": tr.completion_tokens,
                "total_tokens": tr.total_tokens,
                "error": tr.error,
            }
            for tr in result.task_results
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
