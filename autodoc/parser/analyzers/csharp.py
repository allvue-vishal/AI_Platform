"""C#-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_csharp(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract classes, interfaces, methods, and usings from C# source."""
    tree = parse_source(source, "c_sharp")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="c_sharp")

    _walk_nodes(tree.root_node, src, relative_path, result)
    return result


def _walk_nodes(node, src: bytes, rel_path: str, result: FileComponents):
    for child in node.children:
        if child.type == "using_directive":
            result.imports.append(node_text(child, src))
        elif child.type == "namespace_declaration":
            body = child.child_by_field_name("body")
            if body:
                _walk_nodes(body, src, rel_path, result)
        elif child.type in ("class_declaration", "interface_declaration", "struct_declaration"):
            _extract_class(child, src, rel_path, result)
        elif child.type == "file_scoped_namespace_declaration":
            _walk_nodes(child, src, rel_path, result)


def _extract_class(node, src: bytes, rel_path: str, result: FileComponents):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    class_name = node_text(name_node, src)

    bases = []
    for child in node.children:
        if child.type == "base_list":
            for ident in find_descendants_by_type(child, "identifier", "generic_name"):
                bases.append(node_text(ident, src))

    comp_type = {"interface_declaration": "interface", "struct_declaration": "struct"}.get(
        node.type, "class"
    )
    result.components.append(Component(
        name=class_name,
        qualified_name=class_name,
        component_type=comp_type,
        file_path=result.file_path,
        relative_path=rel_path,
        language="c_sharp",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=bases,
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
    calls = find_descendants_by_type(node, "invocation_expression")
    for call in calls:
        fn = call.child_by_field_name("function")
        if fn:
            deps.append(node_text(fn, src))

    result.components.append(Component(
        name=name,
        qualified_name=f"{parent_class}.{name}",
        component_type="method",
        file_path=result.file_path,
        relative_path=rel_path,
        language="c_sharp",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=deps,
        parent_class=parent_class,
    ))
