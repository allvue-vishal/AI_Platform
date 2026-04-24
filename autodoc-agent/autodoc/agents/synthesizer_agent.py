"""Synthesizer agent — generates parent module documentation from child docs using tools."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from autodoc.agents.state import SynthesizerState
from autodoc.agents.tools import SYNTHESIZER_TOOLS
from autodoc.clusterer.module_tree import ModuleNode
from autodoc.docgen.prompts import PARENT_SYSTEM_PROMPT

SYNTHESIZER_SYSTEM = PARENT_SYSTEM_PROMPT + """

You have tools to explore context:
- read_existing_doc(module_name): read documentation of any module for cross-referencing
- get_module_tree(): see the full module hierarchy
- search_components(query): search component names

Strategy:
1. Review the child documentation provided.
2. Optionally use tools to look up sibling modules or verify component references.
3. Write a cohesive parent module overview that synthesizes the children.
4. Output your final documentation directly — do NOT wrap it in code fences.
"""


def build_synthesizer_graph(llm: BaseChatModel) -> StateGraph:
    """Build the synthesizer agent subgraph."""

    llm_with_tools = llm.bind_tools(SYNTHESIZER_TOOLS)

    def agent_node(state: SynthesizerState) -> dict:
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def tool_node(state: SynthesizerState) -> dict:
        last_message = state["messages"][-1]
        tool_map = {t.name: t for t in SYNTHESIZER_TOOLS}
        responses: list[ToolMessage] = []
        for call in last_message.tool_calls:
            fn = tool_map.get(call["name"])
            if fn:
                result = fn.invoke(call["args"])
                responses.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
            else:
                responses.append(ToolMessage(content=f"Unknown tool: {call['name']}", tool_call_id=call["id"]))
        return {"messages": responses}

    def should_continue(state: SynthesizerState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "extract"

    def extract_doc(state: SynthesizerState) -> dict:
        last = state["messages"][-1]
        doc = last.content if isinstance(last, AIMessage) else ""
        return {"generated_doc": doc}

    graph = StateGraph(SynthesizerState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("extract", extract_doc)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "extract": "extract"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract", END)

    return graph


def run_synthesizer(
    llm: BaseChatModel,
    module: ModuleNode,
    child_docs: dict[str, str],
) -> str:
    """Run the synthesizer agent on a parent module."""
    graph = build_synthesizer_graph(llm)
    app = graph.compile()

    parts = []
    for child_name, doc in child_docs.items():
        truncated = doc[:3000] if len(doc) > 3000 else doc
        parts.append(f"### {child_name}\n\n{truncated}")
    combined = "\n\n---\n\n".join(parts)

    user_prompt = (
        f"## Parent Module: {module.name}\n\n"
        f"## Child Module Documentation\n\n{combined}\n\n"
        f"Generate an overview document for the **{module.name}** module "
        f"that ties together its sub-modules. Use tools if you need to look up "
        f"additional context."
    )

    state: SynthesizerState = {
        "messages": [
            SystemMessage(content=SYNTHESIZER_SYSTEM),
            HumanMessage(content=user_prompt),
        ],
        "module": module,
        "child_docs": child_docs,
        "parse_result": None,
        "generated_doc": "",
        "validation_feedback": "",
        "attempt": 0,
        "max_attempts": 3,
    }

    result = app.invoke(state)
    return result.get("generated_doc", f"# {module.name}\n\nSynthesis failed.\n")
