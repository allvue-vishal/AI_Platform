"""Multi-language AST parser using TreeSitter with fallback to regex-based extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from rich.progress import Progress, SpinnerColumn, TextColumn

from autodoc.parser.models import FileComponents, ParseResult
from autodoc.scanner.repo_walker import ScanResult, ScannedFile

_ANALYZERS: dict[str, Callable[[str, str, str], FileComponents]] | None = None


def _get_analyzers() -> dict[str, Callable[[str, str, str], FileComponents]]:
    """Lazy-load per-language analyzers."""
    global _ANALYZERS
    if _ANALYZERS is not None:
        return _ANALYZERS

    from autodoc.parser.analyzers.python import analyze_python
    from autodoc.parser.analyzers.javascript import analyze_javascript
    from autodoc.parser.analyzers.typescript import analyze_typescript
    from autodoc.parser.analyzers.java import analyze_java
    from autodoc.parser.analyzers.c import analyze_c
    from autodoc.parser.analyzers.cpp import analyze_cpp
    from autodoc.parser.analyzers.csharp import analyze_csharp
    from autodoc.parser.analyzers.kotlin import analyze_kotlin
    from autodoc.parser.analyzers.go_lang import analyze_go
    from autodoc.parser.analyzers.rust import analyze_rust

    _ANALYZERS = {
        "python": analyze_python,
        "javascript": analyze_javascript,
        "typescript": analyze_typescript,
        "java": analyze_java,
        "c": analyze_c,
        "cpp": analyze_cpp,
        "c_sharp": analyze_csharp,
        "kotlin": analyze_kotlin,
        "go": analyze_go,
        "rust": analyze_rust,
    }
    return _ANALYZERS


def _read_source(file_path: str) -> str:
    """Read source code with encoding fallback."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return Path(file_path).read_text(encoding=encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return ""


def parse_file(scanned: ScannedFile) -> FileComponents:
    """Parse a single file into its components."""
    source = _read_source(scanned.path)
    if not source.strip():
        return FileComponents(
            file_path=scanned.path,
            relative_path=scanned.relative_path,
            language=scanned.language,
            source_code=source,
        )

    analyzers = _get_analyzers()
    analyzer = analyzers.get(scanned.language)
    if analyzer is None:
        return FileComponents(
            file_path=scanned.path,
            relative_path=scanned.relative_path,
            language=scanned.language,
            source_code=source,
        )

    try:
        result = analyzer(source, scanned.path, scanned.relative_path)
        result.source_code = source
        return result
    except Exception:
        return FileComponents(
            file_path=scanned.path,
            relative_path=scanned.relative_path,
            language=scanned.language,
            source_code=source,
        )


def parse_repository(scan_result: ScanResult, show_progress: bool = True) -> ParseResult:
    """
    Parse all scanned files in a repository and build a unified component map.

    Args:
        scan_result: Output of scan_repository().
        show_progress: Show a rich progress bar.

    Returns:
        ParseResult with all components indexed by component_id.
    """
    result = ParseResult(repo_path=scan_result.repo_path)

    files = scan_result.files
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Parsing source files...", total=len(files))
            for scanned in files:
                fc = parse_file(scanned)
                result.files.append(fc)
                for comp in fc.components:
                    result.all_components[comp.component_id] = comp
                progress.advance(task)
    else:
        for scanned in files:
            fc = parse_file(scanned)
            result.files.append(fc)
            for comp in fc.components:
                result.all_components[comp.component_id] = comp

    return result
