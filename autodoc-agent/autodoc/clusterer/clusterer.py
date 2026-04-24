"""LLM-based module clustering — groups components into logical modules."""

from __future__ import annotations

import json
import re

from rich.console import Console

from autodoc.clusterer.module_tree import ModuleNode
from autodoc.clusterer.token_budget import count_tokens, truncate_to_budget
from autodoc.parser.models import ParseResult

console = Console()

CLUSTER_PROMPT = """\
You are an expert software architect. Given the following list of code components from a repository, \
group them into logical modules.

## Rules
- Group by functional cohesion: related features, shared purpose, or shared directory structure.
- Each component must appear in exactly one module.
- Module names should be concise and descriptive (e.g., "authentication", "database", "api_routes").
- Return ONLY valid JSON — no explanation, no markdown fences.

## Components
{component_list}

## Output Format
Return a JSON object where keys are module names and values are arrays of component IDs:
{{"module_name": ["component_id_1", "component_id_2"], ...}}
"""


def _build_component_list(parse_result: ParseResult, max_tokens: int) -> str:
    """Build a formatted component list that fits within token budget."""
    lines = []
    for comp_id, comp in sorted(parse_result.all_components.items()):
        line = f"- {comp_id} ({comp.component_type}, {comp.language})"
        lines.append(line)

    text = "\n".join(lines)
    if count_tokens(text) > max_tokens:
        text = truncate_to_budget(text, max_tokens)
    return text


def _parse_llm_response(response: str, all_component_ids: set[str]) -> dict[str, list[str]]:
    """Parse the LLM clustering response into a dict of module -> component IDs."""
    cleaned = response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"Could not parse LLM response as JSON: {cleaned[:200]}")

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data)}")

    result: dict[str, list[str]] = {}
    for module_name, comp_ids in data.items():
        if not isinstance(comp_ids, list):
            continue
        valid_ids = [cid for cid in comp_ids if cid in all_component_ids]
        if valid_ids:
            result[module_name] = valid_ids

    return result


def _fallback_clustering(parse_result: ParseResult) -> dict[str, list[str]]:
    """Directory-based fallback if LLM clustering fails."""
    modules: dict[str, list[str]] = {}
    for comp_id, comp in parse_result.all_components.items():
        parts = comp.relative_path.split("/")
        if len(parts) > 1:
            module_name = parts[0]
        else:
            module_name = "root"
        modules.setdefault(module_name, []).append(comp_id)
    return modules


def cluster_modules(
    parse_result: ParseResult,
    llm_call,
    max_tokens_per_module: int = 100_000,
    max_depth: int = 2,
) -> ModuleNode:
    """
    Cluster repository components into a hierarchical module tree using an LLM.

    Args:
        parse_result: Parsed repository components.
        llm_call: Callable(prompt: str) -> str — sends a prompt to the LLM and returns the response.
        max_tokens_per_module: Max tokens for a single module before sub-splitting.
        max_depth: Maximum nesting depth.

    Returns:
        Root ModuleNode of the hierarchical module tree.
    """
    repo_name = parse_result.repo_path.rstrip("/\\").split("/")[-1].split("\\")[-1]
    all_ids = set(parse_result.all_components.keys())

    if len(all_ids) <= 5:
        root = ModuleNode(name=repo_name, components=sorted(all_ids))
        return root

    component_list = _build_component_list(parse_result, max_tokens=max_tokens_per_module // 2)
    prompt = CLUSTER_PROMPT.format(component_list=component_list)

    try:
        console.print("[dim]Clustering components into modules via LLM...[/dim]")
        response = llm_call(prompt)
        modules = _parse_llm_response(response, all_ids)
    except Exception as e:
        console.print(f"[yellow]LLM clustering failed ({e}), using directory-based fallback[/yellow]")
        modules = _fallback_clustering(parse_result)

    assigned = set()
    for comps in modules.values():
        assigned.update(comps)
    unassigned = all_ids - assigned
    if unassigned:
        modules["other"] = sorted(unassigned)

    root = ModuleNode(name=repo_name)
    for module_name, comp_ids in modules.items():
        child = ModuleNode(
            name=module_name,
            components=comp_ids,
            path=module_name,
        )
        root.children[module_name] = child

    return root
