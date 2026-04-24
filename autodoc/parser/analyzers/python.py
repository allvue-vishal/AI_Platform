"""Python-specific TreeSitter analyzer."""

from __future__ import annotations

from autodoc.parser.analyzers._common import (
    parse_source, node_text, node_snippet, find_descendants_by_type,
)
from autodoc.parser.models import Component, FileComponents


def analyze_python(source: str, file_path: str, relative_path: str) -> FileComponents:
    """Extract classes, functions, methods, and imports from Python source."""
    tree = parse_source(source, "python")
    src = source.encode("utf-8")
    result = FileComponents(file_path=file_path, relative_path=relative_path, language="python")

    for node in tree.root_node.children:
        if node.type == "import_statement":
            result.imports.append(node_text(node, src))
        elif node.type == "import_from_statement":
            result.imports.append(node_text(node, src))
        elif node.type == "function_definition":
            _extract_function(node, src, relative_path, result, parent_class=None)
        elif node.type == "decorated_definition":
            body = _unwrap_decorated(node)
            if body and body.type == "function_definition":
                _extract_function(body, src, relative_path, result, parent_class=None)
            elif body and body.type == "class_definition":
                _extract_class(body, src, relative_path, result)
        elif node.type == "class_definition":
            _extract_class(node, src, relative_path, result)

    _resolve_dependencies(result, source)
    return result


def _unwrap_decorated(node):
    """Unwrap a decorated_definition to get the inner definition."""
    for child in node.children:
        if child.type in ("function_definition", "class_definition", "decorated_definition"):
            if child.type == "decorated_definition":
                return _unwrap_decorated(child)
            return child
    return None


def _get_docstring(node, src: bytes) -> str | None:
    """Extract the docstring from a function or class body."""
    body = None
    for child in node.children:
        if child.type == "block":
            body = child
            break
    if body is None:
        return None
    for child in body.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    text = node_text(sub, src)
                    return text.strip("\"'").strip()
    return None


def _extract_function(
    node, src: bytes, relative_path: str,
    result: FileComponents, parent_class: str | None,
) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = node_text(name_node, src)
    qualified = f"{parent_class}.{name}" if parent_class else name
    comp_type = "method" if parent_class else "function"

    comp = Component(
        name=name,
        qualified_name=qualified,
        component_type=comp_type,
        file_path=result.file_path,
        relative_path=relative_path,
        language="python",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        docstring=_get_docstring(node, src),
        parent_class=parent_class,
    )

    calls = find_descendants_by_type(node, "call")
    for call in calls:
        fn = call.child_by_field_name("function")
        if fn:
            comp.depends_on.append(node_text(fn, src))

    result.components.append(comp)


def _extract_class(node, src: bytes, relative_path: str, result: FileComponents) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    class_name = node_text(name_node, src)

    bases = []
    superclasses = node.child_by_field_name("superclasses")
    if superclasses:
        for arg in superclasses.children:
            if arg.type == "identifier":
                bases.append(node_text(arg, src))

    comp = Component(
        name=class_name,
        qualified_name=class_name,
        component_type="class",
        file_path=result.file_path,
        relative_path=relative_path,
        language="python",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=node_snippet(node, src),
        depends_on=list(bases),
        docstring=_get_docstring(node, src),
    )
    result.components.append(comp)

    body = None
    for child in node.children:
        if child.type == "block":
            body = child
            break
    if body is None:
        return

    for child in body.children:
        if child.type == "function_definition":
            _extract_function(child, src, relative_path, result, parent_class=class_name)
        elif child.type == "decorated_definition":
            inner = _unwrap_decorated(child)
            if inner and inner.type == "function_definition":
                _extract_function(inner, src, relative_path, result, parent_class=class_name)


def _resolve_dependencies(result: FileComponents, source: str) -> None:
    """Enrich depends_on with import-based references."""
    imported_names: set[str] = set()
    for imp in result.imports:
        parts = imp.replace(",", " ").split()
        for i, tok in enumerate(parts):
            if tok == "import":
                for name in parts[i + 1:]:
                    clean = name.strip().rstrip(",")
                    if clean and clean != "as" and not clean.startswith("("):
                        imported_names.add(clean.split(".")[-1])

    for comp in result.components:
        comp.depends_on = list(set(comp.depends_on))
