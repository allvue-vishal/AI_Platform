"""Generate metadata.json for the documentation output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from autodoc.parser.models import ParseResult
from autodoc.scanner.repo_walker import ScanResult


def generate_metadata(
    repo_name: str,
    scan_result: ScanResult,
    parse_result: ParseResult,
    model_name: str,
    output_dir: str | Path,
) -> dict:
    """Generate and write metadata.json."""
    meta = {
        "repository": repo_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "autodoc-agent",
        "generator_version": "2.0.0",
        "model": model_name,
        "statistics": {
            "total_files": scan_result.total_files,
            "total_bytes": scan_result.total_bytes,
            "total_components": parse_result.component_count,
            "languages": scan_result.languages,
        },
        "files": [f.relative_path for f in scan_result.files],
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return meta
