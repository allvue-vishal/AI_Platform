"""Rust-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_rust(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract functions, structs, traits, impls, and use declarations from Rust source."""
    tree = parse_source(source, "rust")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="rust")

    for node in tree.root_node.children:
        if node.type == "use_declaration":
            result.imports.append(node_text(node, src))
        elif node.type == "function_item":
            _extract_function(node, src, relative_path, result, parent_class=None)
        elif node.type == "struct_item":
            _extract_struct(node, src, relative_path, result)
        elif node.type == "enum_item":
            _extract_struct(node, src, relative_path, result)
        elif node.type == "trait_item":
            _extract_trait(node, src, relative_path, result)
        elif node.type == "impl_item":
            _extract_impl(node, src, relative_path, result)

    return result


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
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
        language="rust",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=parent_class,
    ))


def _extract_struct(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
    comp_type = "enum" if node.type == "enum_item" else "struct"
    result.components.append(Component(
        name=name,
        qualified_name=name,
        component_type=comp_type,
        file_path=result.file_path,
        relative_path=rel_path,
        language="rust",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
    ))


def _extract_trait(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
    result.components.append(Component(
        name=name,
        qualified_name=name,
        component_type="trait",
        file_path=result.file_path,
        relative_path=rel_path,
        language="rust",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
    ))


def _extract_impl(node, src: bytes, rel_path: str, result: FileComponents):
    type_node = node.child_by_field_name("type")
    if type_node is None:
        return
    impl_name = node_text(type_node, src)

    body = node.child_by_field_name("body")
    if body:
        for child in body.children:
            if child.type == "function_item":
                _extract_function(child, src, rel_path, result, parent_class=impl_name)
