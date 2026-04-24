"""JavaScript-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_javascript(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract functions, classes, and imports from JavaScript source."""
    tree = parse_source(source, "javascript")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="javascript")

    _walk_nodes(tree.root_node, src, relative_path, result, parent_class=None)
    return result


def _walk_nodes(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    for child in node.children:
        if child.type in ("import_statement", "import_declaration"):
            result.imports.append(node_text(child, src))
        elif child.type == "function_declaration":
            _extract_function(child, src, rel_path, result, parent_class)
        elif child.type == "class_declaration":
            _extract_class(child, src, rel_path, result)
        elif child.type == "export_statement":
            _walk_nodes(child, src, rel_path, result, parent_class)
        elif child.type == "lexical_declaration":
            _extract_arrow_functions(child, src, rel_path, result)


def _extract_function(node, src: bytes, rel_path: str, result: FileComponents, parent_class: str | None):
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
    qualified = f"{parent_class}.{name}" if parent_class else name

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
        language="javascript",
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
    heritage = node.child_by_field_name("superclass")
    if heritage:
        bases.append(node_text(heritage, src))

    result.components.append(Component(
        name=class_name,
        qualified_name=class_name,
        component_type="class",
        file_path=result.file_path,
        relative_path=rel_path,
        language="javascript",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=bases,
    ))

    body = node.child_by_field_name("body")
    if body:
        for child in body.children:
            if child.type == "method_definition":
                _extract_function(child, src, rel_path, result, parent_class=class_name)


def _extract_arrow_functions(node, src: bytes, rel_path: str, result: FileComponents):
    """Extract const x = () => {} style function declarations."""
    for decl in node.children:
        if decl.type == "variable_declarator":
            name_node = decl.child_by_field_name("name")
            value_node = decl.child_by_field_name("value")
            if name_node and value_node and value_node.type == "arrow_function":
                name = node_text(name_node, src)
                deps = []
                calls = find_descendants_by_type(value_node, "call_expression")
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
                    language="javascript",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    code_snippet=node_snippet(node, src),
                    depends_on=deps,
                ))
