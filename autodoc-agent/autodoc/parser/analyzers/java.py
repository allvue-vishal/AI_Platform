"""Java-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_java(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract classes, interfaces, methods, and imports from Java source."""
    tree = parse_source(source, "java")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="java")

    for node in tree.root_node.children:
        if node.type == "import_declaration":
            result.imports.append(node_text(node, src))
        elif node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            _extract_class(node, src, relative_path, result)

    return result


def _extract_class(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    class_name = node_text(name_node, src)

    bases = []
    for child in node.children:
        if child.type == "superclass":
            for ident in find_descendants_by_type(child, "type_identifier"):
                bases.append(node_text(ident, src))
        elif child.type == "super_interfaces":
            for ident in find_descendants_by_type(child, "type_identifier"):
                bases.append(node_text(ident, src))

    comp_type = "interface" if node.type == "interface_declaration" else "class"
    result.components.append(Component(
        name=class_name,
        qualified_name=class_name,
        component_type=comp_type,
        file_path=result.file_path,
        relative_path=rel_path,
        language="java",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=bases,
        docstring=_get_javadoc(node, src),
    ))

    body = node.child_by_field_name("body")
    if body:
        for child in body.children:
            if child.type == "method_declaration":
                _extract_method(child, src, rel_path, result, class_name)
            elif child.type == "constructor_declaration":
                _extract_method(child, src, rel_path, result, class_name)


def _extract_method(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)

    deps = []
    calls = find_descendants_by_type(node, "method_invocation")
    for call in calls:
        method_name = call.child_by_field_name("name")
        obj = call.child_by_field_name("object")
        if method_name:
            call_text = node_text(method_name, src)
            if obj:
                call_text = f"{node_text(obj, src)}.{call_text}"
            deps.append(call_text)

    result.components.append(Component(
        name=name,
        qualified_name=f"{parent_class}.{name}",
        component_type="method",
        file_path=result.file_path,
        relative_path=rel_path,
        language="java",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=parent_class,
        docstring=_get_javadoc(node, src),
    ))


def _get_javadoc(node, src: bytes) -> str | None:
    prev = node.prev_sibling
    if prev and prev.type == "block_comment":
        text = node_text(prev, src)
        if text.startswith("/**"):
            return text
    return None
