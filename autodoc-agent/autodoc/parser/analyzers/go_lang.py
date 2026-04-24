"""Go-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_go(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract functions, structs, interfaces, and imports from Go source."""
    tree = parse_source(source, "go")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="go")

    for node in tree.root_node.children:
        if node.type == "import_declaration":
            result.imports.append(node_text(node, src))
        elif node.type == "function_declaration":
            _extract_function(node, src, relative_path, result)
        elif node.type == "method_declaration":
            _extract_method(node, src, relative_path, result)
        elif node.type == "type_declaration":
            _extract_type(node, src, relative_path, result)

    return result


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)

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
        language="go",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
    ))


def _extract_method(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    receiver = node.child_by_field_name("receiver")
    if name_node is None:
        return
    name = node_text(name_node, src)

    receiver_type = ""
    if receiver:
        for child in find_descendants_by_type(receiver, "type_identifier"):
            receiver_type = node_text(child, src)
            break

    qualified = f"{receiver_type}.{name}" if receiver_type else name

    deps = []
    calls = find_descendants_by_type(node, "call_expression")
    for call in calls:
        fn = call.child_by_field_name("function")
        if fn:
            deps.append(node_text(fn, src))

    result.components.append(Component(
        name=name,
        qualified_name=qualified,
        component_type="method",
        file_path=result.file_path,
        relative_path=rel_path,
        language="go",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=receiver_type or None,
    ))


def _extract_type(node, src: bytes, rel_path: str, result: FileComponents):
    for spec in node.children:
        if spec.type == "type_spec":
            name_node = spec.child_by_field_name("name")
            type_node = spec.child_by_field_name("type")
            if name_node is None:
                continue
            name = node_text(name_node, src)
            comp_type = "interface" if type_node and type_node.type == "interface_type" else "struct"
            result.components.append(Component(
                name=name,
                qualified_name=name,
                component_type=comp_type,
                file_path=result.file_path,
                relative_path=rel_path,
                language="go",
                start_line=spec.start_point[0] + 1,
                end_line=spec.end_point[0] + 1,
                code_snippet=node_snippet(spec, src),
            ))
