"""LLM-based module clustering and hierarchical decomposition."""

from autodoc.clusterer.clusterer import cluster_modules
from autodoc.clusterer.module_tree import ModuleNode

__all__ = ["cluster_modules", "ModuleNode"]
