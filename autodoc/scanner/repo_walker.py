"""Walk a repository directory, respecting .gitignore and filtering by language."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

from autodoc.scanner.language_map import detect_language

ALWAYS_IGNORE = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".eggs", "*.egg-info",
}


@dataclass
class ScannedFile:
    """A source file discovered during repository scanning."""
    path: str
    relative_path: str
    language: str
    size_bytes: int


@dataclass
class ScanResult:
    """Aggregated result of a repository scan."""
    repo_path: str
    files: list[ScannedFile] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_bytes: int = 0


def _load_gitignore(repo_root: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from repo root."""
    gitignore = repo_root / ".gitignore"
    if gitignore.is_file():
        with open(gitignore, "r", encoding="utf-8", errors="ignore") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None


def _is_always_ignored(name: str) -> bool:
    """Check against the hardcoded ignore set."""
    for pattern in ALWAYS_IGNORE:
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False


def scan_repository(
    repo_path: str | Path,
    include_languages: set[str] | None = None,
) -> ScanResult:
    """
    Scan a repository directory tree and return all supported source files.

    Args:
        repo_path: Path to the repository root.
        include_languages: If provided, only include files of these languages.

    Returns:
        ScanResult with all discovered source files.
    """
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {repo_root}")

    gitignore_spec = _load_gitignore(repo_root)
    result = ScanResult(repo_path=str(repo_root))

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            d for d in dirnames
            if not _is_always_ignored(d)
            and not (d.startswith(".") and d != ".")
        ]

        for filename in filenames:
            full_path = Path(dirpath) / filename
            rel_path = full_path.relative_to(repo_root).as_posix()

            if gitignore_spec and gitignore_spec.match_file(rel_path):
                continue

            lang = detect_language(str(full_path))
            if lang is None:
                continue
            if include_languages and lang not in include_languages:
                continue

            size = full_path.stat().st_size
            scanned = ScannedFile(
                path=str(full_path),
                relative_path=rel_path,
                language=lang,
                size_bytes=size,
            )
            result.files.append(scanned)
            result.languages[lang] = result.languages.get(lang, 0) + 1
            result.total_files += 1
            result.total_bytes += size

    return result
