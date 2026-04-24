"""Clustering agent — uses tools to interactively explore the codebase and produce module groupings."""

from __future__ import annotations

import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from autodoc.agents.state import ClusteringState
from autodoc.agents.tools import CLUSTERING_TOOLS
from autodoc.clusterer.module_tree import ModuleNode
from autodoc.parser.models import ParseResult

CLUSTERING_SYSTEM = """\
You are an expert software architect. Your task is to organize a codebase \
into logical modules by grouping related components together.

You have tools to inspect the codebase:
- list_components: see all component IDs, types, languages, files
- get_component_details: read source code of a specific component
- get_dependency_info: see dependency relationships
- get_directory_structure: see the file/directory layout

Strategy:
1. First call list_components to see all components.
2. Call get_directory_structure to understand the layout.
3. Optionally inspect a few key components to understand their role.
4. Group components into cohesive modules based on feature, directory, or dependency patterns.

When you are ready, output your final grouping as a JSON object in a fenced \
code block (```json ... ```) where keys are module names and values are arrays \
of component IDs. Every component must appear in exactly one module. Module \
names should be concise and descriptive (e.g., "authentication", "database").
"""


def _parse_modules_from_response(text: str, all_ids: set[str]) -> dict[str, list[str]] | None:
    """Extract JSON module mapping from an AI message."""
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if not json_match:
        json_match = re.search(r"(\{[\s\S]*\})", text)
    if not json_match:
        return None

    try:
        data = json.loads(json_match.group(1))
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    result: dict[str, list[str]] = {}
    for module_name, comp_ids in data.items():
        if isinstance(comp_ids, list):
            valid = [cid for cid in comp_ids if cid in all_ids]
            if valid:
                result[module_name] = valid

    return result if result else None


def build_clustering_graph(llm: BaseChatModel) -> StateGraph:
    """Build the clustering agent subgraph."""

    llm_with_tools = llm.bind_tools(CLUSTERING_TOOLS)

    def agent_node(state: ClusteringState) -> dict:
        """Call the LLM (with tools bound) on the current messages."""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def tool_node(state: ClusteringState) -> dict:
        """Execute any tool calls from the last AI message."""
        last_message = state["messages"][-1]
        tool_responses: list[ToolMessage] = []
        tool_map = {t.name: t for t in CLUSTERING_TOOLS}

        for call in last_message.tool_calls:
            fn = tool_map.get(call["name"])
            if fn:
                result = fn.invoke(call["args"])
                tool_responses.append(
                    ToolMessage(content=str(result), tool_call_id=call["id"])
                )
            else:
                tool_responses.append(
                    ToolMessage(content=f"Unknown tool: {call['name']}", tool_call_id=call["id"])
                )
        return {"messages": tool_responses}

    def should_continue(state: ClusteringState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "done"

    def finalize(state: ClusteringState) -> dict:
        """Parse the final AI response into a ModuleNode tree."""
        parse_result: ParseResult = state["parse_result"]
        all_ids = set(parse_result.all_components.keys())
        repo_name = parse_result.repo_path.rstrip("/\\").split("/")[-1].split("\\")[-1]

        last_ai = state["messages"][-1]
        text = last_ai.content if isinstance(last_ai, AIMessage) else ""

        modules = _parse_modules_from_response(text, all_ids)
        if not modules:
            # Fallback: directory-based
            modules = {}
            for cid, comp in parse_result.all_components.items():
                parts = comp.relative_path.split("/")
                mod = parts[0] if len(parts) > 1 else "root"
                modules.setdefault(mod, []).append(cid)

        assigned = set()
        for cids in modules.values():
            assigned.update(cids)
        unassigned = all_ids - assigned
        if unassigned:
            modules["other"] = sorted(unassigned)

        root = ModuleNode(name=repo_name)
        for mod_name, comp_ids in modules.items():
            root.children[mod_name] = ModuleNode(name=mod_name, components=comp_ids, path=mod_name)

        return {"module_tree": root}

    graph = StateGraph(ClusteringState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "done": "finalize"})
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    return graph


def run_clustering_agent(
    llm: BaseChatModel,
    parse_result: ParseResult,
) -> ModuleNode:
    """Convenience function: run the clustering agent and return the module tree."""
    graph = build_clustering_graph(llm)
    app = graph.compile()

    initial_state: ClusteringState = {
        "messages": [
            SystemMessage(content=CLUSTERING_SYSTEM),
            HumanMessage(content="Analyze this codebase and group the components into logical modules."),
        ],
        "parse_result": parse_result,
        "dep_graph": None,
        "module_tree": None,
        "attempt": 0,
        "max_attempts": 3,
    }

    result = app.invoke(initial_state)
    return result["module_tree"]
