"""CLI entry point — `autodoc generate`, `autodoc config`, `autodoc batch`."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from autodoc.cli.config import AutoDocConfig

console = Console()


def run_pipeline(
    repo_path: str,
    output_dir: str,
    config: AutoDocConfig,
) -> Path:
    """Execute the documentation pipeline via the LangGraph orchestrator."""
    from autodoc.agents.llm import create_chat_model
    from autodoc.agents.orchestrator import build_orchestrator_graph

    repo_path_obj = Path(repo_path).resolve()
    repo_name = repo_path_obj.name

    console.print(Panel(
        "[bold]AutoDoc Agent[/bold] (LangGraph) "
        f"— Generating docs for [cyan]{repo_name}[/cyan]"
    ))

    chat_model = create_chat_model(config, temperature=0.2)
    graph = build_orchestrator_graph(chat_model, config)
    app = graph.compile()

    initial_state = {
        "repo_path": str(repo_path_obj),
        "output_dir": output_dir,
        "scan_result": None,
        "parse_result": None,
        "dep_graph": None,
        "module_tree": None,
        "module_docs": {},
        "overview_doc": "",
        "current_phase": "scan",
        "errors": [],
    }

    app.invoke(initial_state)
    return Path(output_dir)


@click.group()
def cli():
    """AutoDoc Agent — Enterprise auto-documentation from source code."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option(
    "--output", "-o", default=None,
    help="Output directory (default: from config)",
)
@click.option(
    "--model", "-m", default=None,
    help="Override LLM model name",
)
@click.option(
    "--base-url", default=None,
    help="Override LLM base URL",
)
def generate(
    repo_path: str,
    output: str | None,
    model: str | None,
    base_url: str | None,
):
    """Generate documentation for a repository."""
    config = AutoDocConfig()
    if model:
        config.llm_model = model
    if base_url:
        config.llm_base_url = base_url
    if output:
        config.output_dir = output

    console.print("[dim]Configuration:[/dim]")
    console.print(config.display())
    console.print()

    run_pipeline(repo_path, config.output_dir, config)


@cli.command()
def config():
    """Show current configuration."""
    cfg = AutoDocConfig()
    console.print(Panel(cfg.display(), title="AutoDoc Configuration"))


@cli.command()
@click.argument("repos_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o", default="./docs-output",
    help="Base output directory",
)
@click.option(
    "--model", "-m", default=None,
    help="Override LLM model name",
)
@click.option(
    "--base-url", default=None,
    help="Override LLM base URL",
)
def batch(
    repos_file: str,
    output: str,
    model: str | None,
    base_url: str | None,
):
    """Generate docs for multiple repos listed in a YAML file."""
    from autodoc.batch.batch_runner import run_batch

    config = AutoDocConfig()
    if model:
        config.llm_model = model
    if base_url:
        config.llm_base_url = base_url
    run_batch(repos_file, output, config)


if __name__ == "__main__":
    cli()
