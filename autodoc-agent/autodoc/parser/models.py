"""Data models for parsed code components."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Component:
    """A code component extracted from source: function, class, method, etc."""
    name: str
    qualified_name: str
    component_type: str  # "function", "class", "method", "struct", "interface"
    file_path: str
    relative_path: str
    language: str
    start_line: int
    end_line: int
    code_snippet: str
    depends_on: list[str] = field(default_factory=list)  # qualified names of dependencies
    imports: list[str] = field(default_factory=list)
    docstring: str | None = None
    parent_class: str | None = None  # for methods

    @property
    def component_id(self) -> str:
        """Unique identifier: relative_path::qualified_name."""
        return f"{self.relative_path}::{self.qualified_name}"


@dataclass
class FileComponents:
    """All components parsed from a single source file."""
    file_path: str
    relative_path: str
    language: str
    components: list[Component] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    source_code: str = ""


@dataclass
class ParseResult:
    """Aggregated parse results for an entire repository."""
    repo_path: str
    files: list[FileComponents] = field(default_factory=list)
    all_components: dict[str, Component] = field(default_factory=dict)

    @property
    def component_count(self) -> int:
        return len(self.all_components)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def get_component_ids(self) -> list[str]:
        """Return all component IDs sorted by file path."""
        return sorted(self.all_components.keys())
