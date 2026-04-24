"""Build a networkx dependency graph from parsed components."""

from __future__ import annotations

import networkx as nx

from autodoc.parser.models import ParseResult


def build_dependency_graph(parse_result: ParseResult) -> nx.DiGraph:
    """
    Build a directed dependency graph where an edge (A -> B) means A depends on B.

    Nodes carry component metadata as attributes. Edges represent
    function calls, class inheritance, and import-based references.
    """
    graph = nx.DiGraph()

    name_to_ids: dict[str, list[str]] = {}
    for comp_id, comp in parse_result.all_components.items():
        graph.add_node(comp_id, **{
            "name": comp.name,
            "qualified_name": comp.qualified_name,
            "type": comp.component_type,
            "file": comp.relative_path,
            "language": comp.language,
            "start_line": comp.start_line,
            "end_line": comp.end_line,
        })
        name_to_ids.setdefault(comp.name, []).append(comp_id)
        name_to_ids.setdefault(comp.qualified_name, []).append(comp_id)

    for comp_id, comp in parse_result.all_components.items():
        for dep_name in comp.depends_on:
            dep_name_clean = dep_name.split("(")[0].strip()

            target_ids = name_to_ids.get(dep_name_clean, [])
            if not target_ids:
                parts = dep_name_clean.split(".")
                if len(parts) > 1:
                    target_ids = name_to_ids.get(parts[-1], [])

            for target_id in target_ids:
                if target_id != comp_id:
                    graph.add_edge(comp_id, target_id, relation="depends_on")

    return graph


def get_file_dependency_graph(parse_result: ParseResult) -> nx.DiGraph:
    """
    Build a file-level dependency graph. Nodes are file relative paths,
    edges mean "file A has components that depend on components in file B".
    """
    component_graph = build_dependency_graph(parse_result)
    file_graph = nx.DiGraph()

    for fc in parse_result.files:
        file_graph.add_node(fc.relative_path, language=fc.language)

    for comp_id, comp in parse_result.all_components.items():
        for _, target_id in component_graph.out_edges(comp_id):
            target_comp = parse_result.all_components.get(target_id)
            if target_comp and target_comp.relative_path != comp.relative_path:
                file_graph.add_edge(comp.relative_path, target_comp.relative_path)

    return file_graph
