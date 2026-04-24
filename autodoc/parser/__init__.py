"""Multi-language AST parsing using TreeSitter."""

from autodoc.parser.ast_parser import parse_repository
from autodoc.parser.models import Component, ParseResult

__all__ = ["parse_repository", "Component", "ParseResult"]
