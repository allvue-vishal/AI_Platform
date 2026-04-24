"""Module tree data structure for hierarchical decomposition."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ModuleNode:
    """A node in the module tree — can be a leaf or parent module."""
    name: str
    components: list[str] = field(default_factory=list)
    children: dict[str, "ModuleNode"] = field(default_factory=dict)
    path: str = ""

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def all_components(self) -> list[str]:
        """Recursively collect all component IDs under this module."""
        comps = list(self.components)
        for child in self.children.values():
            comps.extend(child.all_components)
        return comps

    def to_dict(self) -> dict:
        result: dict = {"name": self.name}
        if self.components:
            result["components"] = self.components
        if self.children:
            result["children"] = {k: v.to_dict() for k, v in self.children.items()}
        if self.path:
            result["path"] = self.path
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleNode":
        children = {}
        for k, v in data.get("children", {}).items():
            children[k] = cls.from_dict(v)
        return cls(
            name=data["name"],
            components=data.get("components", []),
            children=children,
            path=data.get("path", ""),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "ModuleNode":
        return cls.from_dict(json.loads(json_str))

    def get_leaf_modules(self) -> list["ModuleNode"]:
        """Return all leaf modules in the tree."""
        if self.is_leaf:
            return [self]
        leaves = []
        for child in self.children.values():
            leaves.extend(child.get_leaf_modules())
        return leaves

    def get_processing_order(self) -> list["ModuleNode"]:
        """Return modules in bottom-up order: leaves first, then parents."""
        order: list[ModuleNode] = []
        for child in self.children.values():
            order.extend(child.get_processing_order())
        order.append(self)
        return order

    def summary(self, indent: int = 0) -> str:
        """Human-readable tree summary."""
        prefix = "  " * indent
        kind = "leaf" if self.is_leaf else "parent"
        lines = [f"{prefix}- {self.name} ({kind}, {len(self.all_components)} components)"]
        for child in self.children.values():
            lines.append(child.summary(indent + 1))
        return "\n".join(lines)
