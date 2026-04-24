"""Generate the top-level repository overview documentation."""

from __future__ import annotations

from rich.console import Console

from autodoc.clusterer.module_tree import ModuleNode
from autodoc.clusterer.token_budget import truncate_to_budget
from autodoc.docgen.prompts import OVERVIEW_SYSTEM_PROMPT, OVERVIEW_USER_PROMPT
from autodoc.parser.models import ParseResult
from autodoc.scanner.repo_walker import ScanResult

console = Console()


def generate_overview(
    repo_name: str,
    module_tree: ModuleNode,
    module_docs: dict[str, str],
    parse_result: ParseResult,
    scan_result: ScanResult,
    llm_call,
    max_tokens: int = 100_000,
) -> str:
    """
    Generate the top-level repository overview documentation.

    Args:
        repo_name: Name of the repository.
        module_tree: Root of the module tree.
        module_docs: All generated module docs {module_name: markdown}.
        parse_result: Parsed component data.
        scan_result: Scan statistics.
        llm_call: Callable(system_prompt, user_prompt) -> str.
        max_tokens: Token budget for module summaries in prompt.

    Returns:
        Repository overview as Markdown.
    """
    languages = ", ".join(f"{lang} ({count})" for lang, count in sorted(scan_result.languages.items()))

    summaries = []
    for name, doc in module_docs.items():
        first_para = doc.split("\n\n")[0] if doc else "(no documentation)"
        if len(first_para) > 500:
            first_para = first_para[:500] + "..."
        summaries.append(f"### {name}\n{first_para}")

    combined = "\n\n".join(summaries)
    combined = truncate_to_budget(combined, max_tokens)

    user_prompt = OVERVIEW_USER_PROMPT.format(
        repo_name=repo_name,
        total_files=scan_result.total_files,
        total_components=parse_result.component_count,
        languages=languages,
        module_tree_summary=module_tree.summary(),
        module_summaries=combined,
    )

    console.print("[dim]Generating repository overview...[/dim]")

    try:
        return llm_call(OVERVIEW_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        console.print(f"[red]Error generating overview: {e}[/red]")
        return _fallback_overview(repo_name, module_tree, scan_result, parse_result)


def _fallback_overview(
    repo_name: str, module_tree: ModuleNode,
    scan_result: ScanResult, parse_result: ParseResult,
) -> str:
    lines = [
        f"# {repo_name}",
        "",
        "## Statistics",
        f"- **Files:** {scan_result.total_files}",
        f"- **Components:** {parse_result.component_count}",
        f"- **Languages:** {', '.join(scan_result.languages.keys())}",
        "",
        "## Module Tree",
        "```",
        module_tree.summary(),
        "```",
        "",
    ]
    return "\n".join(lines)
