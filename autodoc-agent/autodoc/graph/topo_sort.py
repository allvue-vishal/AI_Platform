"""Topological sorting and entry point identification."""

from __future__ import annotations

import networkx as nx


def topological_sort(graph: nx.DiGraph) -> list[str]:
    """
    Return nodes in topological order. Falls back to best-effort
    ordering if the graph has cycles.
    """
    try:
        return list(nx.topological_sort(graph))
    except nx.NetworkXUnfeasible:
        return _topo_sort_with_cycles(graph)


def _topo_sort_with_cycles(graph: nx.DiGraph) -> list[str]:
    """Break cycles and produce a reasonable ordering."""
    copy = graph.copy()
    result = []
    while copy.nodes:
        zero_in = [n for n in copy.nodes if copy.in_degree(n) == 0]
        if not zero_in:
            zero_in = [min(copy.nodes, key=lambda n: copy.in_degree(n))]
        for n in sorted(zero_in):
            result.append(n)
            copy.remove_node(n)
    return result


def find_entry_points(graph: nx.DiGraph) -> list[str]:
    """
    Identify entry points: nodes with zero in-degree (nothing depends on them
    being called, but they call other things). These are typically main functions,
    API endpoints, CLI commands, or public interfaces.
    """
    entries = [n for n in graph.nodes if graph.in_degree(n) == 0]
    return sorted(entries)


def find_leaf_components(graph: nx.DiGraph) -> list[str]:
    """
    Identify leaf components: nodes with zero out-degree (they don't depend
    on anything else). These are typically utility functions, base classes, or
    data models.
    """
    leaves = [n for n in graph.nodes if graph.out_degree(n) == 0]
    return sorted(leaves)


def get_dependency_layers(graph: nx.DiGraph) -> list[list[str]]:
    """
    Group nodes into dependency layers for processing order.
    Layer 0 = leaf nodes (no dependencies), layer N = depends only on layers < N.
    """
    order = topological_sort(graph)
    node_to_layer: dict[str, int] = {}

    reversed_order = list(reversed(order))
    for node in reversed_order:
        successors = list(graph.successors(node))
        if not successors:
            node_to_layer[node] = 0
        else:
            max_dep = max(node_to_layer.get(s, 0) for s in successors)
            node_to_layer[node] = max_dep + 1

    layers: dict[int, list[str]] = {}
    for node, layer in node_to_layer.items():
        layers.setdefault(layer, []).append(node)

    return [layers[i] for i in sorted(layers.keys())]
