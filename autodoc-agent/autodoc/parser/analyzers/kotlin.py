"""Kotlin-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_kotlin(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract classes, functions, and imports from Kotlin source."""
    tree = parse_source(source, "kotlin")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="kotlin")

    _walk_nodes(tree.root_node, src, relative_path, result, parent_class=None)
    return result


def _walk_nodes(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    for child in node.children:
        if child.type == "import_list":
            for imp in child.children:
                if imp.type == "import_header":
                    result.imports.append(node_text(imp, src))
        elif child.type == "import_header":
            result.imports.append(node_text(child, src))
        elif child.type == "function_declaration":
            _extract_function(child, src, rel_path, result, parent_class)
        elif child.type == "class_declaration":
            _extract_class(child, src, rel_path, result)
        elif child.type == "object_declaration":
            _extract_class(child, src, rel_path, result)


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    name_node = node.child_by_field_name("name") or _find_simple_identifier(node, src)
    if name_node is None:
        return
    name = node_text(name_node, src)
    qualified = f"{parent_class}.{name}" if parent_class else name

    deps = []
    calls = find_descendants_by_type(node, "call_expression")
    for call in calls:
        fn_parts = []
        for c in call.children:
            if c.type in ("simple_identifier", "navigation_expression"):
                fn_parts.append(node_text(c, src))
                break
        if fn_parts:
            deps.append(fn_parts[0])

    result.components.append(Component(
        name=name,
        qualified_name=qualified,
        component_type="method" if parent_class else "function",
        file_path=result.file_path,
        relative_path=rel_path,
        language="kotlin",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=parent_class,
    ))


def _extract_class(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name") or _find_simple_identifier(node, src)
    if name_node is None:
        return
    class_name = node_text(name_node, src)

    bases = []
    for child in node.children:
        if child.type == "delegation_specifier":
            for ident in find_descendants_by_type(child, "simple_identifier", "type_identifier"):
                bases.append(node_text(ident, src))

    result.components.append(Component(
        name=class_name,
        qualified_name=class_name,
        component_type="class",
        file_path=result.file_path,
        relative_path=rel_path,
        language="kotlin",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=bases,
    ))

    body = node.child_by_field_name("body")
    if body is None:
        for child in node.children:
            if child.type == "class_body":
                body = child
                break
    if body:
        _walk_nodes(body, src, rel_path, result, parent_class=class_name)


def _find_simple_identifier(node, src: bytes):
    for child in node.children:
        if child.type == "simple_identifier":
            return child
    return None
