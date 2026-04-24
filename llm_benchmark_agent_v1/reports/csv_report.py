"""CSV export report generator."""

from __future__ import annotations

import csv
import os
from datetime import datetime

from benchmarks.base import BenchmarkResult
from config import settings


def generate_csv_report(
    results: list[BenchmarkResult],
    output_path: str | None = None,
) -> str:
    """Generate a CSV report from benchmark results. Returns the file path."""
    if not output_path:
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(settings.RESULTS_DIR, f"benchmark_report_{timestamp}.csv")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Model",
            "Category",
            "Avg Score",
            "Avg Latency (s)",
            "Prompt Tokens",
            "Completion Tokens",
            "Total Tokens",
            "Estimated Cost ($)",
            "Task ID",
            "Task Score",
            "Task Latency (s)",
            "Task Error",
        ])

        for result in results:
            for tr in result.task_results:
                writer.writerow([
                    result.model,
                    result.category,
                    result.avg_score,
                    result.avg_latency,
                    result.total_prompt_tokens,
                    result.total_completion_tokens,
                    result.total_tokens,
                    result.estimated_cost,
                    tr.task_id,
                    tr.score,
                    tr.latency_seconds,
                    tr.error or "",
                ])

    return output_path
