"""Extension-to-language mapping and TreeSitter grammar registry."""

from __future__ import annotations

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".cs": "c_sharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
}

SUPPORTED_LANGUAGES = {
    "python", "javascript", "typescript", "java", "kotlin",
    "c", "cpp", "c_sharp", "go", "rust",
}


def detect_language(file_path: str) -> str | None:
    """Return the language name for a file path, or None if unsupported."""
    from pathlib import Path
    ext = Path(file_path).suffix.lower()
    if ext in (".h", ".hpp", ".hxx"):
        return _guess_header_language(file_path)
    return LANGUAGE_EXTENSIONS.get(ext)


def _guess_header_language(file_path: str) -> str:
    """Heuristic: .h files are C unless sibling .cpp/.cxx exists."""
    from pathlib import Path
    p = Path(file_path)
    stem = p.stem
    parent = p.parent
    cpp_exts = {".cpp", ".cxx", ".cc"}
    for ext in cpp_exts:
        if (parent / f"{stem}{ext}").exists():
            return "cpp"
    return "c"
