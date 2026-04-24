"""Generate a self-contained HTML documentation viewer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template
from rich.console import Console

console = Console()

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "viewer.html"


def generate_html(
    repo_name: str,
    module_docs: dict[str, str],
    overview_doc: str,
    output_dir: str | Path,
) -> Path:
    """
    Generate a self-contained index.html with all documentation embedded.

    Args:
        repo_name: Repository name.
        module_docs: {module_name: markdown_content}.
        overview_doc: Overview markdown.
        output_dir: Where to write index.html.

    Returns:
        Path to the generated index.html.
    """
    docs = {"overview": overview_doc}
    docs.update(module_docs)

    module_names = sorted(module_docs.keys())

    template_str = _TEMPLATE_PATH.read_text(encoding="utf-8")
    template = Template(template_str)

    html = template.render(
        repo_name=repo_name,
        module_names=module_names,
        docs_json=json.dumps(docs),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "index.html"
    html_path.write_text(html, encoding="utf-8")

    console.print(f"  [green]Wrote[/green] index.html ({len(html) // 1024} KB)")
    return html_path
