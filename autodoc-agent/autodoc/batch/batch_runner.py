"""Batch runner — process multiple repositories from a YAML config."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from autodoc.cli.config import AutoDocConfig

console = Console()


def run_batch(
    repos_file: str,
    base_output_dir: str,
    config: AutoDocConfig,
) -> dict:
    """
    Run the documentation pipeline on multiple repositories.

    repos_yaml format::

        repos:
          - path: /path/to/repo1
            name: repo1
          - path: /path/to/repo2

    Args:
        repos_file: Path to the YAML file listing repositories.
        base_output_dir: Base directory for output.
        config: AutoDoc configuration.

    Returns:
        Summary dict with per-repo status.
    """
    from autodoc.cli.main import run_pipeline

    repos_path = Path(repos_file)
    with open(repos_path, "r", encoding="utf-8") as f:
        repos_config = yaml.safe_load(f)

    repos = repos_config.get("repos", [])
    if not repos:
        console.print("[red]No repositories found in config file.[/red]")
        return {}

    console.print(
        f"\n[bold]Batch mode:[/bold] Processing {len(repos)} "
        "repositories\n"
    )

    results: dict[str, dict] = {}
    base_out = Path(base_output_dir)

    for i, repo_entry in enumerate(repos, 1):
        repo_path = repo_entry.get("path", "")
        repo_name = repo_entry.get("name", Path(repo_path).name)

        console.rule(f"[{i}/{len(repos)}] {repo_name}")

        output_dir = base_out / repo_name
        start = time.time()

        try:
            run_pipeline(repo_path, str(output_dir), config)
            elapsed = time.time() - start
            results[repo_name] = {
                "status": "success",
                "output": str(output_dir),
                "elapsed_seconds": round(elapsed, 1),
            }
            console.print(
                f"[green]Completed {repo_name} in "
                f"{elapsed:.1f}s[/green]\n"
            )
        except Exception as e:
            elapsed = time.time() - start
            results[repo_name] = {
                "status": "error",
                "error": str(e),
                "elapsed_seconds": round(elapsed, 1),
            }
            console.print(f"[red]Failed {repo_name}: {e}[/red]\n")

    _print_summary(results)
    _write_batch_report(results, base_out)
    return results


def _print_summary(results: dict[str, dict]) -> None:
    table = Table(title="Batch Results")
    table.add_column("Repository", style="cyan")
    table.add_column("Status")
    table.add_column("Time (s)", justify="right")

    for name, info in results.items():
        if info["status"] == "success":
            status = "[green]OK[/green]"
        else:
            err = info.get("error", "")[:50]
            status = f"[red]FAILED: {err}[/red]"
        table.add_row(name, status, str(info["elapsed_seconds"]))

    console.print(table)


def _write_batch_report(
    results: dict[str, dict],
    output_dir: Path,
) -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_repos": len(results),
        "successful": sum(
            1 for r in results.values() if r["status"] == "success"
        ),
        "failed": sum(
            1 for r in results.values() if r["status"] == "error"
        ),
        "repos": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "batch_report.json"
    report_path.write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    console.print(f"\nBatch report written to {report_path}")
