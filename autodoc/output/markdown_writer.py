"""Write generated documentation to Markdown files."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from autodoc.clusterer.module_tree import ModuleNode

console = Console()


def write_module_docs(
    output_dir: str | Path,
    module_tree: ModuleNode,
    module_docs: dict[str, str],
    overview_doc: str,
    module_tree_json: str,
) -> Path:
    """
    Write all generated documentation to the output directory.

    Structure:
        output_dir/
            overview.md
            module_tree.json
            modules/
                module_name.md
                ...

    Returns:
        Path to the output directory.
    """
    out = Path(output_dir)
    modules_dir = out / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    (out / "overview.md").write_text(overview_doc, encoding="utf-8")
    console.print("  [green]Wrote[/green] overview.md")

    (out / "module_tree.json").write_text(module_tree_json, encoding="utf-8")
    console.print("  [green]Wrote[/green] module_tree.json")

    for module_name, doc in module_docs.items():
        safe_name = module_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        file_path = modules_dir / f"{safe_name}.md"
        file_path.write_text(doc, encoding="utf-8")
        console.print(f"  [green]Wrote[/green] modules/{safe_name}.md")

    return out
