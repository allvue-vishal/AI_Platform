"""Shared TreeSitter utilities used by all language analyzers."""

from __future__ import annotations

import tree_sitter_language_pack as tslp

_PARSER_CACHE: dict[str, object] = {}


def get_parser(language: str):
    """Return a cached TreeSitter parser for the given language."""
    if language not in _PARSER_CACHE:
        import tree_sitter as ts
        parser = ts.Parser(tslp.get_language(language))
        _PARSER_CACHE[language] = parser
    return _PARSER_CACHE[language]


def parse_source(source: str, language: str):
    """Parse source code and return the TreeSitter tree."""
    parser = get_parser(language)
    return parser.parse(source.encode("utf-8"))


def node_text(node, source_bytes: bytes) -> str:
    """Extract the text of a TreeSitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def node_snippet(node, source_bytes: bytes, max_lines: int = 50) -> str:
    """Extract a code snippet, truncating long bodies."""
    text = node_text(node, source_bytes)
    lines = text.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n    # ... ({len(lines) - max_lines} more lines)"
    return text


def find_children_by_type(node, *types: str) -> list:
    """Find all direct children matching any of the given types."""
    return [child for child in node.children if child.type in types]


def find_descendants_by_type(node, *types: str) -> list:
    """Find all descendants (recursive) matching any of the given types."""
    results = []
    stack = list(node.children)
    while stack:
        child = stack.pop()
        if child.type in types:
            results.append(child)
        stack.extend(child.children)
    return results
