"""Repository scanning — file enumeration with .gitignore support and language detection."""

from autodoc.scanner.repo_walker import scan_repository
from autodoc.scanner.language_map import LANGUAGE_EXTENSIONS, detect_language

__all__ = ["scan_repository", "LANGUAGE_EXTENSIONS", "detect_language"]
