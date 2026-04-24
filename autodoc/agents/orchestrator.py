"""Orchestrator — supervisor StateGraph that coordinates the full documentation pipeline.

Wires together: scan -> parse -> graph -> cluster -> docgen -> synthesize -> overview -> output.
Each phase is a node; clustering and docgen delegate to their respective agent subgraphs.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from rich.console import Console
from rich.panel import Panel

from autodoc.agents.clustering_agent import run_clustering_agent
from autodoc.agents.doc_writer_agent import run_doc_writer
from autodoc.agents.state import OrchestratorState
from autodoc.agents.synthesizer_agent import run_synthesizer
from autodoc.agents.tools import set_tool_context
from autodoc.agents.validator_agent import validate_doc
from autodoc.cli.config import AutoDocConfig

console = Console()


def build_orchestrator_graph(
    llm: BaseChatModel,
    config: AutoDocConfig,
) -> StateGraph:
    """Build the top-level orchestrator graph."""

    # ------------------------------------------------------------------
    # Node: scan
    # ------------------------------------------------------------------
    def scan_node(state: OrchestratorState) -> dict:
        from autodoc.scanner import scan_repository

        console.print("\n[bold]Phase 1/8:[/bold] Scanning repository...")
        scan_result = scan_repository(state["repo_path"])
        console.print(
            f"  Found {scan_result.total_files} source files "
            f"across {len(scan_result.languages)} languages"
        )
        if scan_result.total_files == 0:
            return {
                "scan_result": scan_result,
                "current_phase": "error",
                "errors": ["No supported source files found."],
            }
        return {"scan_result": scan_result, "current_phase": "parse"}

    # ------------------------------------------------------------------
    # Node: parse
    # ------------------------------------------------------------------
    def parse_node(state: OrchestratorState) -> dict:
        from autodoc.parser import parse_repository

        console.print("\n[bold]Phase 2/8:[/bold] Parsing source code...")
        parse_result = parse_repository(state["scan_result"])
        console.print(
            f"  Extracted {parse_result.component_count} components "
            f"from {parse_result.file_count} files"
        )
        return {"parse_result": parse_result, "current_phase": "graph"}

    # ------------------------------------------------------------------
    # Node: build graph
    # ------------------------------------------------------------------
    def graph_node(state: OrchestratorState) -> dict:
        from autodoc.graph import build_dependency_graph

        console.print("\n[bold]Phase 3/8:[/bold] Building dependency graph...")
        dep_graph = build_dependency_graph(state["parse_result"])
        console.print(
            f"  Graph: {dep_graph.number_of_nodes()} nodes, "
            f"{dep_graph.number_of_edges()} edges"
        )
        set_tool_context(
            parse_result=state["parse_result"],
            dep_graph=dep_graph,
        )
        return {"dep_graph": dep_graph, "current_phase": "cluster"}

    # ------------------------------------------------------------------
    # Node: cluster (delegates to ClusteringAgent)
    # ------------------------------------------------------------------
    def cluster_node(state: OrchestratorState) -> dict:
        console.print("\n[bold]Phase 4/8:[/bold] Clustering into modules (agent)...")
        try:
            module_tree = run_clustering_agent(llm, state["parse_result"])
            console.print(f"  Module tree:\n{module_tree.summary(indent=2)}")
            set_tool_context(module_tree=module_tree)
            return {"module_tree": module_tree, "current_phase": "docgen"}
        except Exception as e:
            console.print(f"  [yellow]Clustering agent failed ({e}), using directory fallback[/yellow]")
            from autodoc.clusterer import cluster_modules
            import litellm

            model = config.get_litellm_model()
            api_base = config.llm_base_url
            api_key = config.llm_api_key
            if config.llm_provider == "litellm_proxy":
                litellm.api_base = api_base
                litellm.api_key = api_key

            def call_simple(prompt: str) -> str:
                resp = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    api_base=api_base,
                    api_key=api_key,
                    temperature=0.2,
                )
                return resp.choices[0].message.content

            module_tree = cluster_modules(
                state["parse_result"],
                llm_call=call_simple,
                max_tokens_per_module=config.max_tokens_per_module,
                max_depth=config.max_depth,
            )
            set_tool_context(module_tree=module_tree)
            return {"module_tree": module_tree, "current_phase": "docgen"}

    # ------------------------------------------------------------------
    # Node: docgen (delegates to DocWriterAgent for each leaf module)
    # ------------------------------------------------------------------
    def docgen_node(state: OrchestratorState) -> dict:
        console.print("\n[bold]Phase 5/8:[/bold] Generating module documentation (agent)...")
        module_tree = state["module_tree"]
        parse_result = state["parse_result"]
        tree_summary = module_tree.summary()

        module_docs: dict[str, str] = state.get("module_docs") or {}
        processing_order = module_tree.get_processing_order()

        for mod in processing_order:
            if mod.name == module_tree.name and mod.children:
                continue

            if mod.is_leaf:
                console.print(f"  [dim]DocWriter agent: {mod.name} ({len(mod.all_components)} components)[/dim]")
                doc = run_doc_writer(
                    llm, mod, parse_result, tree_summary,
                    max_tokens=config.max_tokens_per_leaf,
                )

                if config.validation_enabled:
                    is_valid, feedback = validate_doc(doc, mod.name, parse_result)
                    if not is_valid:
                        console.print(f"  [yellow]Validation failed for {mod.name}, retrying...[/yellow]")
                        doc = run_doc_writer(
                            llm, mod, parse_result, tree_summary,
                            max_tokens=config.max_tokens_per_leaf,
                        )

                module_docs[mod.name] = doc
                set_tool_context(module_docs=module_docs)

        return {"module_docs": module_docs, "current_phase": "synthesize"}

    # ------------------------------------------------------------------
    # Node: synthesize (parent modules via SynthesizerAgent)
    # ------------------------------------------------------------------
    def synthesize_node(state: OrchestratorState) -> dict:
        console.print("\n[bold]Phase 6/8:[/bold] Synthesizing parent modules (agent)...")
        module_tree = state["module_tree"]
        module_docs = dict(state.get("module_docs") or {})
        processing_order = module_tree.get_processing_order()

        for mod in processing_order:
            if mod.name == module_tree.name and mod.children:
                continue
            if not mod.is_leaf and mod.children:
                child_docs = {
                    child.name: module_docs.get(child.name, "")
                    for child in mod.children.values()
                }
                console.print(f"  [dim]Synthesizer agent: {mod.name} ({len(child_docs)} children)[/dim]")
                doc = run_synthesizer(llm, mod, child_docs)

                if config.validation_enabled:
                    is_valid, feedback = validate_doc(doc, mod.name, state.get("parse_result"))
                    if not is_valid:
                        console.print(f"  [yellow]Validation failed for {mod.name}, retrying...[/yellow]")
                        doc = run_synthesizer(llm, mod, child_docs)

                module_docs[mod.name] = doc
                set_tool_context(module_docs=module_docs)

        return {"module_docs": module_docs, "current_phase": "overview"}

    # ------------------------------------------------------------------
    # Node: overview
    # ------------------------------------------------------------------
    def overview_node(state: OrchestratorState) -> dict:
        from autodoc.docgen.overview_generator import generate_overview

        console.print("\n[bold]Phase 7/8:[/bold] Generating repository overview...")
        repo_name = Path(state["repo_path"]).resolve().name
        module_docs = state.get("module_docs") or {}

        def call_with_system(system_prompt: str, user_prompt: str) -> str:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            return resp.content

        overview = generate_overview(
            repo_name=repo_name,
            module_tree=state["module_tree"],
            module_docs=module_docs,
            parse_result=state["parse_result"],
            scan_result=state["scan_result"],
            llm_call=call_with_system,
            max_tokens=config.max_tokens_per_module,
        )
        return {"overview_doc": overview, "current_phase": "output"}

    # ------------------------------------------------------------------
    # Node: output
    # ------------------------------------------------------------------
    def output_node(state: OrchestratorState) -> dict:
        from autodoc.output.markdown_writer import write_module_docs
        from autodoc.output.html_generator import generate_html
        from autodoc.output.metadata import generate_metadata

        console.print("\n[bold]Phase 8/8:[/bold] Writing output...")
        out_path = Path(state["output_dir"])
        module_docs = state.get("module_docs") or {}
        overview_doc = state.get("overview_doc", "")
        module_tree = state["module_tree"]
        repo_name = Path(state["repo_path"]).resolve().name

        write_module_docs(out_path, module_tree, module_docs, overview_doc, module_tree.to_json())
        generate_html(repo_name, module_docs, overview_doc, out_path)
        generate_metadata(repo_name, state["scan_result"], state["parse_result"], config.llm_model, out_path)

        console.print(Panel(
            f"[bold green]Done![/bold green] Documentation written to [cyan]{out_path}[/cyan]\n"
            f"Open [cyan]{out_path / 'index.html'}[/cyan] in a browser to view."
        ))
        return {"current_phase": "done"}

    # ------------------------------------------------------------------
    # Error node
    # ------------------------------------------------------------------
    def error_node(state: OrchestratorState) -> dict:
        errors = state.get("errors") or []
        console.print(f"[red]Pipeline failed: {'; '.join(errors)}[/red]")
        return {"current_phase": "done"}

    # ------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------
    def after_scan(state: OrchestratorState) -> str:
        if state.get("errors"):
            return "error"
        return "parse"

    # ------------------------------------------------------------------
    # Wire the graph
    # ------------------------------------------------------------------
    graph = StateGraph(OrchestratorState)

    graph.add_node("scan", scan_node)
    graph.add_node("parse", parse_node)
    graph.add_node("graph", graph_node)
    graph.add_node("cluster", cluster_node)
    graph.add_node("docgen", docgen_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("overview", overview_node)
    graph.add_node("output", output_node)
    graph.add_node("error", error_node)

    graph.set_entry_point("scan")
    graph.add_conditional_edges("scan", after_scan, {"parse": "parse", "error": "error"})
    graph.add_edge("parse", "graph")
    graph.add_edge("graph", "cluster")
    graph.add_edge("cluster", "docgen")
    graph.add_edge("docgen", "synthesize")
    graph.add_edge("synthesize", "overview")
    graph.add_edge("overview", "output")
    graph.add_edge("output", END)
    graph.add_edge("error", END)

    return graph
