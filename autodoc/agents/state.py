"""LangGraph state definitions for all agents."""

from __future__ import annotations

from typing import Annotated, TypedDict

import networkx as nx
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from autodoc.clusterer.module_tree import ModuleNode
from autodoc.parser.models import ParseResult
from autodoc.scanner.repo_walker import ScanResult


class OrchestratorState(TypedDict, total=False):
    """Top-level state flowing through the orchestrator graph."""
    repo_path: str
    output_dir: str
    scan_result: ScanResult | None
    parse_result: ParseResult | None
    dep_graph: nx.DiGraph | None
    module_tree: ModuleNode | None
    module_docs: dict[str, str]
    overview_doc: str
    current_phase: str
    errors: list[str]


class ClusteringState(TypedDict, total=False):
    """State for the clustering agent subgraph."""
    messages: Annotated[list[BaseMessage], add_messages]
    parse_result: ParseResult | None
    dep_graph: nx.DiGraph | None
    module_tree: ModuleNode | None
    attempt: int
    max_attempts: int


class DocWriterState(TypedDict, total=False):
    """State for a single doc-writer invocation."""
    messages: Annotated[list[BaseMessage], add_messages]
    module: ModuleNode | None
    parse_result: ParseResult | None
    dep_graph: nx.DiGraph | None
    module_tree_summary: str
    generated_doc: str
    validation_feedback: str
    attempt: int
    max_attempts: int


class ValidatorState(TypedDict, total=False):
    """State for the validator agent."""
    messages: Annotated[list[BaseMessage], add_messages]
    module_name: str
    generated_doc: str
    parse_result: ParseResult | None
    is_valid: bool
    feedback: str


class SynthesizerState(TypedDict, total=False):
    """State for the synthesizer agent (parent modules)."""
    messages: Annotated[list[BaseMessage], add_messages]
    module: ModuleNode | None
    child_docs: dict[str, str]
    parse_result: ParseResult | None
    generated_doc: str
    validation_feedback: str
    attempt: int
    max_attempts: int
