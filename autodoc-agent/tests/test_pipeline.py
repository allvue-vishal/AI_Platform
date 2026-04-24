"""Smoke test — validates scanning, parsing, graph building, clustering,
and the v2 agent imports/tool wiring."""

import json
from pathlib import Path

from autodoc.scanner import scan_repository
from autodoc.parser import parse_repository
from autodoc.graph import (
    build_dependency_graph,
    topological_sort,
    find_entry_points,
)
from autodoc.clusterer import cluster_modules
from autodoc.clusterer.module_tree import ModuleNode
from autodoc.output.html_generator import generate_html
from autodoc.output.markdown_writer import write_module_docs
from autodoc.output.metadata import generate_metadata

REPO_PATH = Path(__file__).parent.parent / "autodoc"


def test_scan():
    result = scan_repository(REPO_PATH)
    assert result.total_files > 0, "Should find source files"
    assert "python" in result.languages, "Should detect Python"
    print(f"  Scanned: {result.total_files} files")
    return result


def test_parse(scan_result):
    result = parse_repository(scan_result, show_progress=False)
    assert result.component_count > 0, "Should extract components"
    print(
        f"  Parsed: {result.component_count} components "
        f"from {result.file_count} files"
    )
    return result


def test_graph(parse_result):
    graph = build_dependency_graph(parse_result)
    assert graph.number_of_nodes() > 0
    entries = find_entry_points(graph)
    topological_sort(graph)
    print(
        f"  Graph: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges, "
        f"{len(entries)} entry points"
    )
    return graph


def test_cluster(parse_result):
    def mock_llm(prompt: str) -> str:
        comp_ids = list(parse_result.all_components.keys())
        mid = len(comp_ids) // 2
        return json.dumps({
            "core_pipeline": comp_ids[:mid],
            "utilities_and_support": comp_ids[mid:],
        })

    tree = cluster_modules(parse_result, llm_call=mock_llm)
    assert isinstance(tree, ModuleNode)
    assert len(tree.children) > 0
    print(f"  Module tree:\n{tree.summary(indent=2)}")
    return tree


def test_agent_imports():
    """Verify all v2 agent modules import cleanly."""
    from autodoc.agents import build_orchestrator_graph  # noqa: F401
    from autodoc.agents.llm import create_chat_model  # noqa: F401
    from autodoc.agents.tools import (
        set_tool_context,  # noqa: F401
        CLUSTERING_TOOLS,
        DOC_WRITER_TOOLS,
        SYNTHESIZER_TOOLS,
    )
    from autodoc.agents.clustering_agent import run_clustering_agent  # noqa: F401
    from autodoc.agents.doc_writer_agent import run_doc_writer  # noqa: F401
    from autodoc.agents.synthesizer_agent import run_synthesizer  # noqa: F401
    from autodoc.agents.validator_agent import validate_doc  # noqa: F401

    assert len(CLUSTERING_TOOLS) == 4
    assert len(DOC_WRITER_TOOLS) == 5
    assert len(SYNTHESIZER_TOOLS) == 3
    print("  All agent imports OK")


def test_tools(parse_result, dep_graph):
    """Verify tools work once context is populated."""
    from autodoc.agents.tools import (
        set_tool_context,
        list_components,
        get_directory_structure,
        search_components,
    )

    set_tool_context(parse_result=parse_result, dep_graph=dep_graph)

    result = list_components.invoke({})
    assert len(result) > 0
    print(f"  list_components: {len(result.splitlines())} lines")

    result = get_directory_structure.invoke({})
    assert len(result) > 0
    print(f"  get_directory_structure: {len(result.splitlines())} lines")

    result = search_components.invoke({"query": "scan"})
    print(f"  search_components('scan'): {result[:80]}...")


def test_validator():
    """Verify structural validation works."""
    from autodoc.agents.validator_agent import validate_doc

    good_doc = (
        "# Module Overview\n\n"
        "This module does things.\n\n"
        "## Components\n\n"
        "### function: `foo`\n\n"
        "## API Reference\n\n"
        "```mermaid\nflowchart TD\n  A --> B\n```\n"
    )
    is_valid, feedback = validate_doc(good_doc, "test_mod", None)
    assert is_valid, f"Expected valid, got: {feedback}"
    print(f"  Good doc validated: {feedback}")

    bad_doc = "Short."
    is_valid, feedback = validate_doc(bad_doc, "bad_mod", None)
    assert not is_valid
    print(f"  Bad doc rejected: {feedback}")


def test_output(scan_result, parse_result, module_tree):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        module_docs = {
            "core_pipeline": "# Core\n\nCore pipeline module.",
            "utilities_and_support": "# Utils\n\nUtility functions.",
        }
        overview = "# AutoDoc Agent\n\nAuto documentation generator."

        write_module_docs(
            tmp, module_tree, module_docs,
            overview, module_tree.to_json(),
        )
        html_path = generate_html(
            "autodoc-agent", module_docs, overview, tmp,
        )
        generate_metadata(
            "autodoc-agent", scan_result,
            parse_result, "mock-model", tmp,
        )

        assert html_path.exists()
        assert (Path(tmp) / "overview.md").exists()
        assert (Path(tmp) / "metadata.json").exists()
        print(
            f"  Output OK — index.html "
            f"{html_path.stat().st_size // 1024} KB"
        )


if __name__ == "__main__":
    print("=" * 60)
    print("AutoDoc Agent v2 — Pipeline Smoke Test")
    print("=" * 60)

    print("\n1. Scanning repository...")
    scan_result = test_scan()

    print("\n2. Parsing source code...")
    parse_result = test_parse(scan_result)

    print("\n3. Building dependency graph...")
    dep_graph = test_graph(parse_result)

    print("\n4. Clustering (mock LLM)...")
    module_tree = test_cluster(parse_result)

    print("\n5. Agent imports...")
    test_agent_imports()

    print("\n6. Tool wiring...")
    test_tools(parse_result, dep_graph)

    print("\n7. Validator...")
    test_validator()

    print("\n8. Output writing...")
    test_output(scan_result, parse_result, module_tree)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
