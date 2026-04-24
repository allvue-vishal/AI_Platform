"""C++-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_cpp(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract classes, functions, methods, and includes from C++ source."""
    tree = parse_source(source, "cpp")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="cpp")

    for node in tree.root_node.children:
        if node.type == "preproc_include":
            result.imports.append(node_text(node, src))
        elif node.type == "function_definition":
            _extract_function(node, src, relative_path, result, parent_class=None)
        elif node.type == "class_specifier":
            _extract_class(node, src, relative_path, result)
        elif node.type == "struct_specifier":
            _extract_struct(node, src, relative_path, result)
        elif node.type == "namespace_definition":
            _walk_namespace(node, src, relative_path, result)

    return result


def _walk_namespace(node, src: bytes, rel_path: str, result: FileComponents):
    body = node.child_by_field_name("body")
    if body:
        for child in body.children:
            if child.type == "function_definition":
                _extract_function(child, src, rel_path, result, parent_class=None)
            elif child.type == "class_specifier":
                _extract_class(child, src, rel_path, result)


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    declarator = node.child_by_field_name("declarator")
    if declarator is None:
        return
    name_node = declarator.child_by_field_name("declarator")
    if name_node is None:
        name_node = declarator
    name = node_text(name_node, src).split("(")[0].split("::")[-1].strip("*& ")
    if not name:
        return
    qualified = f"{parent_class}::{name}" if parent_class else name

    deps = []
    calls = find_descendants_by_type(node, "call_expression")
    for call in calls:
        fn = call.child_by_field_name("function")
        if fn:
            deps.append(node_text(fn, src))

    result.components.append(Component(
        name=name,
        qualified_name=qualified,
        component_type="method" if parent_class else "function",
        file_path=result.file_path,
        relative_path=rel_path,
        language="cpp",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=parent_class,
    ))


def _extract_class(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    class_name = node_text(name_node, src)

    bases = []
    for child in node.children:
        if child.type == "base_class_clause":
            for ident in find_descendants_by_type(child, "type_identifier"):
                bases.append(node_text(ident, src))

    result.components.append(Component(
        name=class_name,
        qualified_name=class_name,
        component_type="class",
        file_path=result.file_path,
        relative_path=rel_path,
        language="cpp",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=bases,
    ))

    body = node.child_by_field_name("body")
    if body:
        for child in body.children:
            if child.type == "function_definition":
                _extract_function(child, src, rel_path, result, parent_class=class_name)
            elif child.type == "declaration":
                pass  # member variables — skipped for now


def _extract_struct(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
    result.components.append(Component(
        name=name,
        qualified_name=name,
        component_type="struct",
        file_path=result.file_path,
        relative_path=rel_path,
        language="cpp",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
    ))
