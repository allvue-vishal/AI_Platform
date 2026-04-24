"""Rich CLI table report generator — full model comparison."""

from __future__ import annotations

import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from benchmarks.base import BenchmarkResult


def generate_cli_report(results: list[BenchmarkResult]) -> str:
    """Print a rich CLI report directly to stdout and return a plain-text summary."""
    console = Console(width=160)

    models = sorted(set(r.model for r in results))
    categories = sorted(set(r.category for r in results))

    model_avgs: dict[str, float] = {}
    for model in models:
        mrs = [r for r in results if r.model == model]
        model_avgs[model] = sum(r.avg_score for r in mrs) / len(mrs) if mrs else 0

    overall_best = max(models, key=lambda m: model_avgs[m]) if models else "N/A"

    # -- Winner banner --
    banner = (
        f"[bold green]Overall Best Model: {overall_best}[/bold green]  "
        f"(avg score: {model_avgs.get(overall_best, 0):.1f}/100)"
    )
    console.print()
    console.print(Panel(banner, title="[bold]LLM Benchmark Results[/bold]", border_style="cyan", padding=(1, 3)))
    console.print()

    # -- Scores table --
    scores_table = Table(
        title="Scores by Category (0-100)",
        show_header=True, header_style="bold cyan", show_lines=True, title_style="bold",
    )
    scores_table.add_column("Category", style="bold", min_width=22)
    for model in models:
        scores_table.add_column(model, justify="center", min_width=14)
    scores_table.add_column("Best", justify="center", style="bold green", min_width=14)

    for cat in categories:
        row: list[str] = [cat]
        cat_scores: dict[str, float] = {}
        for model in models:
            match = [r for r in results if r.category == cat and r.model == model]
            if match:
                s = match[0].avg_score
                cat_scores[model] = s
                color = "bold green" if s >= 80 else ("yellow" if s >= 60 else ("dark_orange" if s >= 40 else "bold red"))
                row.append(f"[{color}]{s:.1f}[/{color}]")
            else:
                row.append("[dim]--[/dim]")
        best_m = max(cat_scores, key=cat_scores.get) if cat_scores else "--"
        row.append(best_m)
        scores_table.add_row(*row)

    avg_row: list[str] = ["[bold]AVERAGE[/bold]"]
    for model in models:
        avg_row.append(f"[bold]{model_avgs[model]:.1f}[/bold]")
    avg_row.append(f"[bold]{overall_best}[/bold]")
    scores_table.add_row(*avg_row)
    console.print(scores_table)
    console.print()

    # -- Latency table --
    lat_table = Table(
        title="Average Latency (seconds)",
        show_header=True, header_style="bold cyan", show_lines=True, title_style="bold",
    )
    lat_table.add_column("Category", style="bold", min_width=22)
    for model in models:
        lat_table.add_column(model, justify="center", min_width=14)
    for cat in categories:
        row = [cat]
        for model in models:
            match = [r for r in results if r.category == cat and r.model == model]
            row.append(f"{match[0].avg_latency:.2f}s" if match else "--")
        lat_table.add_row(*row)
    console.print(lat_table)
    console.print()

    # -- Cost & tokens table --
    cost_table = Table(
        title="Cost & Token Usage (per model, all categories combined)",
        show_header=True, header_style="bold cyan", show_lines=True, title_style="bold",
    )
    cost_table.add_column("Model", style="bold", min_width=18)
    cost_table.add_column("Avg Score", justify="center")
    cost_table.add_column("Avg Latency (s)", justify="center")
    cost_table.add_column("Total Tokens", justify="right")
    cost_table.add_column("Est. Cost ($)", justify="right")
    for model in models:
        mrs = [r for r in results if r.model == model]
        avg_lat = sum(r.avg_latency for r in mrs) / len(mrs) if mrs else 0
        total_tok = sum(r.total_tokens for r in mrs)
        total_cost = sum(r.estimated_cost for r in mrs)
        cost_table.add_row(
            model, f"{model_avgs[model]:.1f}", f"{avg_lat:.2f}",
            f"{total_tok:,}", f"${total_cost:.6f}",
        )
    console.print(cost_table)
    console.print()

    # -- Best model per category --
    rec_table = Table(
        title="Best Model per Use Case",
        show_header=True, header_style="bold cyan", show_lines=True, title_style="bold",
    )
    rec_table.add_column("Use Case", style="bold", min_width=22)
    rec_table.add_column("Recommended Model", style="bold green")
    rec_table.add_column("Score", justify="center")
    rec_table.add_column("Latency", justify="center")
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        if cat_results:
            best = max(cat_results, key=lambda r: r.avg_score)
            rec_table.add_row(cat, best.model, f"{best.avg_score:.1f}", f"{best.avg_latency:.2f}s")
    console.print(rec_table)
    console.print()

    # Return a plain text summary
    lines = [f"Overall Best: {overall_best} ({model_avgs.get(overall_best, 0):.1f}/100)"]
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        if cat_results:
            best = max(cat_results, key=lambda r: r.avg_score)
            lines.append(f"  {cat}: {best.model} ({best.avg_score:.1f})")
    return "\n".join(lines)
