"""C-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_c(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract functions, structs, and includes from C source."""
    tree = parse_source(source, "c")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="c")

    for node in tree.root_node.children:
        if node.type == "preproc_include":
            result.imports.append(node_text(node, src))
        elif node.type == "function_definition":
            _extract_function(node, src, relative_path, result)
        elif node.type == "struct_specifier":
            _extract_struct(node, src, relative_path, result)
        elif node.type == "declaration":
            _check_function_declaration(node, src, relative_path, result)
        elif node.type == "type_definition":
            _extract_typedef(node, src, relative_path, result)

    return result


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents):
    declarator = node.child_by_field_name("declarator")
    if declarator is None:
        return
    name_node = declarator.child_by_field_name("declarator")
    if name_node is None:
        name_node = declarator
    name = node_text(name_node, src).strip("*").strip()

    deps = []
    calls = find_descendants_by_type(node, "call_expression")
    for call in calls:
        fn = call.child_by_field_name("function")
        if fn:
            deps.append(node_text(fn, src))

    result.components.append(Component(
        name=name,
        qualified_name=name,
        component_type="function",
        file_path=result.file_path,
        relative_path=rel_path,
        language="c",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
    ))


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
        language="c",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
    ))


def _extract_typedef(node, src: bytes, rel_path: str, result: FileComponents):
    text = node_text(node, src)
    name = text.rstrip(";").split()[-1] if text else None
    if name:
        result.components.append(Component(
            name=name,
            qualified_name=name,
            component_type="typedef",
            file_path=result.file_path,
            relative_path=rel_path,
            language="c",
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            code_snippet=node_snippet(node, src),
        ))


def _check_function_declaration(node, src: bytes, rel_path: str, result: FileComponents):
    """Check if a declaration is a function prototype."""
    declarator = node.child_by_field_name("declarator")
    if declarator and declarator.type == "function_declarator":
        name_node = declarator.child_by_field_name("declarator")
        if name_node:
            name = node_text(name_node, src).strip("*").strip()
            result.components.append(Component(
                name=name,
                qualified_name=name,
                component_type="function",
                file_path=result.file_path,
                relative_path=rel_path,
                language="c",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                code_snippet=node_snippet(node, src),
            ))
