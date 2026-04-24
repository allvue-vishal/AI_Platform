"""Tool definitions for LangGraph agents.

Each tool is a @tool-decorated function that agents can call via bind_tools().
Tools access shared context (parse_result, dep_graph, module_tree, module_docs)
through a ToolContext holder that is set once at pipeline start.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import networkx as nx
from langchain_core.tools import tool

from autodoc.clusterer.module_tree import ModuleNode
from autodoc.parser.models import ParseResult


@dataclass
class ToolContext:
    """Mutable holder for shared data that tools read from."""
    parse_result: ParseResult | None = None
    dep_graph: nx.DiGraph | None = None
    module_tree: ModuleNode | None = None
    module_docs: dict[str, str] = field(default_factory=dict)


_ctx = ToolContext()


def set_tool_context(
    parse_result: ParseResult | None = None,
    dep_graph: nx.DiGraph | None = None,
    module_tree: ModuleNode | None = None,
    module_docs: dict[str, str] | None = None,
) -> None:
    """Populate the global tool context before running any agent."""
    if parse_result is not None:
        _ctx.parse_result = parse_result
    if dep_graph is not None:
        _ctx.dep_graph = dep_graph
    if module_tree is not None:
        _ctx.module_tree = module_tree
    if module_docs is not None:
        _ctx.module_docs = module_docs


# ---------------------------------------------------------------------------
# Clustering tools
# ---------------------------------------------------------------------------

@tool
def list_components() -> str:
    """List all component IDs with their type, language, and file path."""
    if not _ctx.parse_result:
        return "Error: parse_result not available."
    lines = []
    for cid, comp in sorted(_ctx.parse_result.all_components.items()):
        lines.append(f"{cid}  ({comp.component_type}, {comp.language}, {comp.relative_path})")
    if not lines:
        return "No components found."
    return "\n".join(lines[:500])  # cap to avoid token overflow


@tool
def get_component_details(component_id: str) -> str:
    """Read the full source code and metadata of a single component by its ID."""
    if not _ctx.parse_result:
        return "Error: parse_result not available."
    comp = _ctx.parse_result.all_components.get(component_id)
    if not comp:
        return f"Component '{component_id}' not found."
    header = (
        f"Name: {comp.qualified_name}\n"
        f"Type: {comp.component_type}\n"
        f"File: {comp.relative_path}:{comp.start_line}-{comp.end_line}\n"
        f"Language: {comp.language}\n"
        f"Docstring: {comp.docstring or '(none)'}\n"
        f"Depends on: {', '.join(comp.depends_on) or '(none)'}\n"
        f"Imports: {', '.join(comp.imports) or '(none)'}\n"
    )
    return header + f"\n--- Source ---\n{comp.code_snippet}"


@tool
def get_dependency_info(component_id: str) -> str:
    """Get what a component depends on and what depends on it."""
    if not _ctx.dep_graph:
        return "Error: dependency graph not available."
    if component_id not in _ctx.dep_graph:
        return f"Component '{component_id}' not in the dependency graph."

    depends_on = list(_ctx.dep_graph.successors(component_id))
    depended_by = list(_ctx.dep_graph.predecessors(component_id))
    return (
        f"Component: {component_id}\n"
        f"Depends on ({len(depends_on)}): {', '.join(depends_on[:30]) or '(none)'}\n"
        f"Depended on by ({len(depended_by)}): {', '.join(depended_by[:30]) or '(none)'}"
    )


@tool
def get_directory_structure() -> str:
    """Get the file/directory tree of the scanned repository."""
    if not _ctx.parse_result:
        return "Error: parse_result not available."
    dirs: dict[str, list[str]] = {}
    for fc in _ctx.parse_result.files:
        parts = fc.relative_path.rsplit("/", 1)
        directory = parts[0] if len(parts) > 1 else "."
        filename = parts[-1]
        dirs.setdefault(directory, []).append(filename)

    lines = []
    for d in sorted(dirs):
        lines.append(f"{d}/")
        for f in sorted(dirs[d]):
            lines.append(f"  {f}")
    return "\n".join(lines[:300])


# ---------------------------------------------------------------------------
# Doc-writer / synthesizer tools
# ---------------------------------------------------------------------------

@tool
def read_source_code(component_id: str) -> str:
    """Read the full source code of a component. Same as get_component_details."""
    return get_component_details.invoke(component_id)


@tool
def traverse_dependencies(component_id: str) -> str:
    """Traverse dependencies of a component — both inbound and outbound."""
    return get_dependency_info.invoke(component_id)


@tool
def search_components(query: str) -> str:
    """Search for components whose ID or qualified name matches a pattern (case-insensitive)."""
    if not _ctx.parse_result:
        return "Error: parse_result not available."
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches = []
    for cid, comp in _ctx.parse_result.all_components.items():
        if pattern.search(cid) or pattern.search(comp.qualified_name):
            matches.append(f"{cid}  ({comp.component_type}, {comp.language})")
    if not matches:
        return f"No components matching '{query}'."
    return "\n".join(matches[:100])


@tool
def read_existing_doc(module_name: str) -> str:
    """Read already-generated documentation for a sibling module (for cross-referencing)."""
    doc = _ctx.module_docs.get(module_name)
    if doc:
        if len(doc) > 4000:
            return doc[:4000] + "\n\n... (truncated)"
        return doc
    return f"No documentation found for module '{module_name}'."


@tool
def get_module_tree() -> str:
    """Get the full module tree summary showing all modules and their component counts."""
    if not _ctx.module_tree:
        return "Error: module tree not available."
    return _ctx.module_tree.summary()


# ---------------------------------------------------------------------------
# Tool groups for binding to agents
# ---------------------------------------------------------------------------

CLUSTERING_TOOLS = [
    list_components,
    get_component_details,
    get_dependency_info,
    get_directory_structure,
]

DOC_WRITER_TOOLS = [
    read_source_code,
    traverse_dependencies,
    search_components,
    read_existing_doc,
    get_module_tree,
]

SYNTHESIZER_TOOLS = [
    read_existing_doc,
    get_module_tree,
    search_components,
]
