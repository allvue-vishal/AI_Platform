"""CLI entry point for the LLM Benchmark Agent."""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from config import settings

console = Console()


@click.group()
@click.option("--proxy-url", envvar="LITELLM_PROXY_URL", default=None, help="LiteLLM proxy URL")
@click.option("--api-key", envvar="LITELLM_API_KEY", default=None, help="LiteLLM API key")
@click.option("--judge-model", envvar="JUDGE_MODEL", default=None, help="Model to use as LLM judge")
def cli(proxy_url: str | None, api_key: str | None, judge_model: str | None):
    """LLM Benchmark Agent — evaluate and compare all models on your LiteLLM proxy."""
    if proxy_url:
        settings.LITELLM_PROXY_URL = proxy_url
    if api_key:
        settings.LITELLM_API_KEY = api_key
    if judge_model:
        settings.JUDGE_MODEL = judge_model


# ────────────────────────────────────────────────────────────────
#  PRIMARY COMMAND: auto-discover all models, benchmark everything
# ────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--categories", "-c", default="", help="Comma-separated category slugs (empty = all)")
@click.option("--output", "-o", default=None, help="Path for the HTML report (auto-generated if omitted)")
def run(categories: str, output: str | None):
    """Auto-discover ALL models on the proxy and benchmark them across all categories.

    This is the main command. It will:
      1. Connect to your LiteLLM proxy
      2. Discover every available model
      3. Run all benchmark categories (or a filtered set) against every model
      4. Print a comparison table in the terminal
      5. Generate an HTML report with charts
    """
    from models.discovery import list_models as _list_models
    from benchmarks.registry import ALL_BENCHMARKS, get_benchmark_by_category, get_all_categories
    from evaluation.scorer import run_benchmark_for_model
    from agent.tools import get_results_store, _save_result

    # Step 1 — discover models
    console.print(Panel(
        f"Connecting to [bold]{settings.LITELLM_PROXY_URL}[/bold] ...",
        title="Step 1: Model Discovery",
        border_style="blue",
    ))
    discovered = asyncio.run(_list_models())
    if not discovered:
        console.print("[bold red]No models found on the proxy. Check LITELLM_PROXY_URL and LITELLM_API_KEY.[/bold red]")
        return

    model_ids = [m.id for m in discovered]
    console.print(f"[green]Found {len(model_ids)} models:[/green]")
    for mid in model_ids:
        console.print(f"  [cyan]{mid}[/cyan]")
    console.print()

    # Step 2 — resolve categories
    if categories.strip():
        cat_slugs = [c.strip() for c in categories.split(",") if c.strip()]
        benchmarks = []
        for slug in cat_slugs:
            b = get_benchmark_by_category(slug)
            if b:
                benchmarks.append(b)
            else:
                console.print(f"[yellow]Unknown category: {slug}[/yellow]")
        if not benchmarks:
            console.print("[red]No valid categories found.[/red]")
            console.print(f"Available: {', '.join(get_all_categories())}")
            return
    else:
        benchmarks = list(ALL_BENCHMARKS)

    total_runs = len(model_ids) * len(benchmarks)
    console.print(Panel(
        f"[bold]{len(benchmarks)}[/bold] categories x [bold]{len(model_ids)}[/bold] models = "
        f"[bold]{total_runs}[/bold] benchmark runs",
        title="Step 2: Running Benchmarks",
        border_style="blue",
    ))

    # Step 3 — run benchmarks
    judge_model = settings.JUDGE_MODEL or None
    results_store = get_results_store()
    current = 0

    for model in model_ids:
        console.rule(f"[bold]{model}[/bold]")
        for bench in benchmarks:
            current += 1
            console.print(
                f"  [{current}/{total_runs}] [cyan]{bench.category}[/cyan]",
                end=" ... ",
            )
            result = run_benchmark_for_model(bench, model, judge_model)
            results_store.append(result)
            _save_result(result)

            score_color = "green" if result.avg_score >= 70 else ("yellow" if result.avg_score >= 40 else "red")
            console.print(
                f"[{score_color}]{result.avg_score:.1f}/100[/{score_color}]  "
                f"({result.avg_latency:.2f}s)"
            )

    console.print()

    # Step 4 — generate reports
    console.print(Panel("Generating reports ...", title="Step 3: Reports", border_style="blue"))

    from reports.cli_report import generate_cli_report
    from reports.html_report import generate_html_report
    from reports.csv_report import generate_csv_report

    generate_cli_report(results_store)

    html_path = generate_html_report(results_store, output)
    console.print(f"\n[bold green]HTML report saved to:[/bold green] {html_path}")

    csv_path = generate_csv_report(results_store)
    console.print(f"[bold green]CSV  report saved to:[/bold green] {csv_path}")


# ────────────────────────────────────────────────────────────────
#  BENCHMARK: manual model selection (optional auto-discover)
# ────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--models", "-m", "model_names", default=None,
              help="Comma-separated model IDs. If omitted, all proxy models are discovered automatically.")
@click.option("--categories", "-c", default="", help="Comma-separated category slugs (empty = all)")
@click.option("--all", "run_all", is_flag=True, help="Run all categories")
def benchmark(model_names: str | None, categories: str, run_all: bool):
    """Run benchmarks against specified (or all discovered) models."""
    from benchmarks.registry import ALL_BENCHMARKS, get_benchmark_by_category, get_all_categories
    from evaluation.scorer import run_benchmark_for_model
    from agent.tools import get_results_store, _save_result

    # Resolve models
    if model_names:
        model_list = [m.strip() for m in model_names.split(",") if m.strip()]
    else:
        from models.discovery import list_models as _list_models
        console.print(f"[bold]No --models flag provided. Discovering all models on {settings.LITELLM_PROXY_URL} ...[/bold]")
        discovered = asyncio.run(_list_models())
        if not discovered:
            console.print("[bold red]No models found. Check your proxy URL and API key.[/bold red]")
            return
        model_list = [m.id for m in discovered]
        console.print(f"[green]Auto-discovered {len(model_list)} models: {', '.join(model_list)}[/green]\n")

    if not model_list:
        console.print("[red]No models to benchmark.[/red]")
        return

    # Resolve categories
    if run_all or not categories.strip():
        benchmarks = list(ALL_BENCHMARKS)
    else:
        cat_slugs = [c.strip() for c in categories.split(",") if c.strip()]
        benchmarks = []
        for slug in cat_slugs:
            b = get_benchmark_by_category(slug)
            if b:
                benchmarks.append(b)
            else:
                console.print(f"[yellow]Unknown category: {slug}[/yellow]")
        if not benchmarks:
            console.print("[red]No valid categories found.[/red]")
            console.print(f"Available: {', '.join(get_all_categories())}")
            return

    judge_model = settings.JUDGE_MODEL or None
    results_store = get_results_store()
    total = len(model_list) * len(benchmarks)
    current = 0

    console.print(Panel(
        f"Running [bold]{len(benchmarks)}[/bold] benchmarks across [bold]{len(model_list)}[/bold] models "
        f"({total} total benchmark runs)",
        title="Benchmark Run",
        border_style="blue",
    ))

    for model in model_list:
        console.rule(f"[bold]{model}[/bold]")
        for bench in benchmarks:
            current += 1
            console.print(f"  [{current}/{total}] [cyan]{bench.category}[/cyan]", end=" ... ")
            result = run_benchmark_for_model(bench, model, judge_model)
            results_store.append(result)
            _save_result(result)
            score_color = "green" if result.avg_score >= 70 else ("yellow" if result.avg_score >= 40 else "red")
            console.print(
                f"[{score_color}]{result.avg_score:.1f}/100[/{score_color}]  "
                f"({result.avg_latency:.2f}s)"
            )

    console.print("\n[bold green]All benchmarks complete![/bold green]\n")

    from reports.cli_report import generate_cli_report
    generate_cli_report(results_store)

    from reports.html_report import generate_html_report
    html_path = generate_html_report(results_store)
    console.print(f"\n[bold green]HTML report saved to:[/bold green] {html_path}")

    from reports.csv_report import generate_csv_report
    csv_path = generate_csv_report(results_store)
    console.print(f"[bold green]CSV  report saved to:[/bold green] {csv_path}")


# ────────────────────────────────────────────────────────────────
#  UTILITY COMMANDS
# ────────────────────────────────────────────────────────────────
@cli.command()
def models():
    """List available models on the LiteLLM proxy."""
    from models.discovery import list_models as _list_models

    console.print(f"[bold]Connecting to {settings.LITELLM_PROXY_URL}...[/bold]")
    discovered = asyncio.run(_list_models())

    if not discovered:
        console.print("[red]No models found. Check your proxy URL and API key.[/red]")
        return

    console.print(f"\n[green]Found {len(discovered)} models:[/green]\n")
    for m in discovered:
        parts = [f"[bold]{m.id}[/bold]"]
        if m.owned_by:
            parts.append(f"(by {m.owned_by})")
        if m.max_tokens:
            parts.append(f"max_tokens={m.max_tokens}")
        if m.supports_function_calling:
            parts.append("[cyan]tools[/cyan]")
        console.print("  " + " ".join(parts))


@cli.command()
def categories():
    """List all available benchmark categories."""
    from benchmarks.registry import ALL_BENCHMARKS

    console.print("\n[bold]Available Benchmark Categories:[/bold]\n")
    for b in ALL_BENCHMARKS:
        tasks = b.get_tasks()
        console.print(f"  [cyan]{b.category}[/cyan] -- {b.description} ({len(tasks)} tasks)")
    console.print()


@cli.command()
@click.option("--format", "-f", "fmt", type=click.Choice(["cli", "html", "csv", "all"]), default="all")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--from-dir", default=None, help="Load results from a directory of JSON files")
def report(fmt: str, output: str | None, from_dir: str | None):
    """Generate a report from benchmark results."""
    from agent.tools import get_results_store

    results = list(get_results_store())

    if from_dir:
        results = _load_results_from_dir(from_dir)

    if not results:
        console.print("[red]No results available. Run benchmarks first or specify --from-dir.[/red]")
        return

    if fmt in ("cli", "all"):
        from reports.cli_report import generate_cli_report
        generate_cli_report(results)

    if fmt in ("html", "all"):
        from reports.html_report import generate_html_report
        path = generate_html_report(results, output)
        console.print(f"[green]HTML report saved to: {path}[/green]")

    if fmt in ("csv", "all"):
        from reports.csv_report import generate_csv_report
        csv_out = output.replace(".html", ".csv") if output and output.endswith(".html") else output
        path = generate_csv_report(results, csv_out)
        console.print(f"[green]CSV report saved to: {path}[/green]")


@cli.command()
@click.option("--agent-model", default=None, help="Model for the agent itself to use")
def agent(agent_model: str | None):
    """Start interactive agent mode."""
    from agent.orchestrator import run_agent_interactive
    run_agent_interactive()


def _load_results_from_dir(dir_path: str):
    """Load BenchmarkResult objects from saved JSON files."""
    import json as json_mod
    from benchmarks.base import BenchmarkResult, TaskResult

    results = []
    if not os.path.isdir(dir_path):
        console.print(f"[red]Directory not found: {dir_path}[/red]")
        return results

    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(dir_path, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json_mod.load(f)
            task_results = [
                TaskResult(
                    task_id=tr["task_id"],
                    model=data["model"],
                    score=tr["score"],
                    response="",
                    latency_seconds=tr["latency_seconds"],
                    prompt_tokens=tr["prompt_tokens"],
                    completion_tokens=tr["completion_tokens"],
                    total_tokens=tr["total_tokens"],
                    error=tr.get("error"),
                )
                for tr in data.get("task_results", [])
            ]
            results.append(BenchmarkResult(
                benchmark_name=data["benchmark_name"],
                category=data["category"],
                model=data["model"],
                avg_score=data["avg_score"],
                avg_latency=data["avg_latency"],
                total_prompt_tokens=data["total_prompt_tokens"],
                total_completion_tokens=data["total_completion_tokens"],
                total_tokens=data["total_tokens"],
                estimated_cost=data["estimated_cost"],
                task_results=task_results,
            ))
        except Exception as e:
            console.print(f"[yellow]Skipping {fname}: {e}[/yellow]")

    return results


if __name__ == "__main__":
    cli()
