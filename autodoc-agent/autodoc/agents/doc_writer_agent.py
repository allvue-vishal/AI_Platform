"""Doc writer agent — generates documentation for leaf modules using tools and self-validation.

If a module is too large, it recursively delegates sub-sections to a child
invocation of the same graph (recursive subgraph pattern).
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from autodoc.agents.state import DocWriterState
from autodoc.agents.tools import DOC_WRITER_TOOLS
from autodoc.clusterer.module_tree import ModuleNode
from autodoc.clusterer.token_budget import count_tokens
from autodoc.docgen.prompts import LEAF_SYSTEM_PROMPT, format_source_blocks
from autodoc.parser.models import ParseResult

DOC_WRITER_SYSTEM = LEAF_SYSTEM_PROMPT + """

You have tools to explore the codebase while writing documentation:
- read_source_code(component_id): read the full source of a component
- traverse_dependencies(component_id): see inbound/outbound dependencies
- search_components(query): find components by name pattern
- read_existing_doc(module_name): read already-generated sibling docs for cross-refs
- get_module_tree(): see the full module hierarchy

Strategy:
1. Review the components listed in your task.
2. Use tools to read source code and dependencies as needed.
3. Write comprehensive Markdown documentation with Mermaid diagrams.
4. Output your final documentation directly — do NOT wrap it in code fences.
"""


def _build_initial_prompt(module: ModuleNode, parse_result: ParseResult, tree_summary: str) -> str:
    """Build the initial user message describing the module to document."""
    components = []
    for cid in module.all_components:
        comp = parse_result.all_components.get(cid)
        if comp:
            components.append(comp)

    source_preview = format_source_blocks(components[:10])  # cap preview
    comp_list = "\n".join(
        f"- {c.component_id} ({c.component_type}, {c.language})" for c in components
    )

    return (
        f"## Module: {module.name}\n\n"
        f"## Components ({len(components)} total)\n{comp_list}\n\n"
        f"## Module Tree\n```\n{tree_summary}\n```\n\n"
        f"## Source Code Preview\n{source_preview}\n\n"
        f"Generate comprehensive documentation for the **{module.name}** module. "
        f"Use tools to read additional source code or dependencies as needed."
    )


def build_doc_writer_graph(llm: BaseChatModel) -> StateGraph:
    """Build the doc-writer agent subgraph with tool-calling loop."""

    llm_with_tools = llm.bind_tools(DOC_WRITER_TOOLS)

    def agent_node(state: DocWriterState) -> dict:
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def tool_node(state: DocWriterState) -> dict:
        last_message = state["messages"][-1]
        tool_map = {t.name: t for t in DOC_WRITER_TOOLS}
        responses: list[ToolMessage] = []
        for call in last_message.tool_calls:
            fn = tool_map.get(call["name"])
            if fn:
                result = fn.invoke(call["args"])
                responses.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
            else:
                responses.append(ToolMessage(content=f"Unknown tool: {call['name']}", tool_call_id=call["id"]))
        return {"messages": responses}

    def should_continue(state: DocWriterState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "extract"

    def extract_doc(state: DocWriterState) -> dict:
        """Extract the final documentation from the last AI message."""
        last = state["messages"][-1]
        doc = last.content if isinstance(last, AIMessage) else ""
        return {"generated_doc": doc}

    graph = StateGraph(DocWriterState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("extract", extract_doc)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "extract": "extract"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract", END)

    return graph


def run_doc_writer(
    llm: BaseChatModel,
    module: ModuleNode,
    parse_result: ParseResult,
    module_tree_summary: str,
    max_tokens: int = 50_000,
) -> str:
    """
    Run the doc-writer agent on a single leaf module.

    If the module's source exceeds max_tokens, it splits the module and
    runs a child doc-writer on each half, then merges the results.
    """
    total_source_tokens = 0
    for cid in module.all_components:
        comp = parse_result.all_components.get(cid)
        if comp:
            total_source_tokens += count_tokens(comp.code_snippet)

    if total_source_tokens > max_tokens and len(module.all_components) > 4:
        return _recursive_delegation(llm, module, parse_result, module_tree_summary, max_tokens)

    graph = build_doc_writer_graph(llm)
    app = graph.compile()

    initial_prompt = _build_initial_prompt(module, parse_result, module_tree_summary)

    state: DocWriterState = {
        "messages": [
            SystemMessage(content=DOC_WRITER_SYSTEM),
            HumanMessage(content=initial_prompt),
        ],
        "module": module,
        "parse_result": parse_result,
        "dep_graph": None,
        "module_tree_summary": module_tree_summary,
        "generated_doc": "",
        "validation_feedback": "",
        "attempt": 0,
        "max_attempts": 3,
    }

    result = app.invoke(state)
    return result.get("generated_doc", f"# {module.name}\n\nDocumentation generation failed.\n")


def _recursive_delegation(
    llm: BaseChatModel,
    module: ModuleNode,
    parse_result: ParseResult,
    tree_summary: str,
    max_tokens: int,
) -> str:
    """Split a large module into halves and document each recursively, then merge."""
    comps = module.all_components
    mid = len(comps) // 2

    sub_a = ModuleNode(name=f"{module.name}_part1", components=comps[:mid], path=module.path)
    sub_b = ModuleNode(name=f"{module.name}_part2", components=comps[mid:], path=module.path)

    doc_a = run_doc_writer(llm, sub_a, parse_result, tree_summary, max_tokens)
    doc_b = run_doc_writer(llm, sub_b, parse_result, tree_summary, max_tokens)

    merged = (
        f"# {module.name}\n\n"
        f"This module is documented in two parts due to its size.\n\n"
        f"---\n\n{doc_a}\n\n---\n\n{doc_b}"
    )
    return merged
