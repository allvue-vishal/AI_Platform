"""Prompt templates for documentation generation."""

from __future__ import annotations

EXTENSION_TO_LANG = {
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "java": "java", "kotlin": "kotlin", "c": "c", "cpp": "cpp",
    "c_sharp": "csharp", "go": "go", "rust": "rust",
}

# ---------------------------------------------------------------------------
# Leaf module documentation
# ---------------------------------------------------------------------------

LEAF_SYSTEM_PROMPT = """\
You are a senior software documentation writer creating comprehensive, \
developer-friendly documentation for a code module.

Write in clear, professional Markdown. Include:
1. **Module Overview** — purpose, responsibility, and design rationale
2. **Key Components** — classes, functions, structs with concise descriptions
3. **API Reference** — signatures, parameters, return types, exceptions
4. **Dependencies** — what this module depends on and what depends on it
5. **Architecture Diagram** — a Mermaid `flowchart` showing component relationships
6. **Data Flow** — a Mermaid `sequenceDiagram` if the module processes data through stages
7. **Usage Examples** — short code snippets showing how to use key functions/classes

Rules:
- Use Mermaid fenced blocks (```mermaid) for ALL diagrams.
- Do NOT use spaces in Mermaid node IDs; use camelCase or underscores.
- Keep descriptions concise but technically accurate.
- If a component has a docstring, incorporate its intent (don't just repeat it).
- Output ONLY Markdown. No preamble or sign-off.
"""

LEAF_USER_PROMPT = """\
## Module: {module_name}

## Repository Module Tree
```
{module_tree_summary}
```

## Source Code

{source_code_blocks}

Generate comprehensive documentation for the **{module_name}** module.
"""

# ---------------------------------------------------------------------------
# Parent module synthesis
# ---------------------------------------------------------------------------

PARENT_SYSTEM_PROMPT = """\
You are a senior software architect creating a module overview that synthesizes \
documentation from child sub-modules into a cohesive architectural narrative.

Write in clear, professional Markdown. Include:
1. **Module Overview** — high-level purpose and how sub-modules collaborate
2. **Architecture Diagram** — a Mermaid `flowchart` showing sub-module relationships and data flow
3. **Sub-Module Summary** — brief description of each child module's role
4. **Key Interfaces** — how modules communicate (shared types, APIs, events)
5. **Data Flow** — a Mermaid diagram showing how data moves across sub-modules

Rules:
- Synthesize, don't duplicate. Refer to sub-module docs for details.
- Mermaid diagrams must use camelCase or underscore node IDs, no spaces.
- Output ONLY Markdown.
"""

PARENT_USER_PROMPT = """\
## Parent Module: {module_name}

## Child Module Documentation

{child_docs}

Generate an overview document for the **{module_name}** module that ties together its sub-modules.
"""

# ---------------------------------------------------------------------------
# Repository overview
# ---------------------------------------------------------------------------

OVERVIEW_SYSTEM_PROMPT = """\
You are a senior software architect writing the top-level documentation overview for \
an entire code repository. This is the first page developers see.

Write in clear, professional Markdown. Include:
1. **Project Overview** — what the project does, key features, target users
2. **Architecture Overview** — high-level system architecture as a Mermaid `flowchart`
3. **Module Map** — table or list summarizing each top-level module
4. **Technology Stack** — languages, frameworks, key libraries
5. **Data Flow** — a Mermaid `sequenceDiagram` showing the primary data/request flow
6. **Getting Started** — brief pointers for new developers

Rules:
- This should read like a professional project README + architecture guide.
- Mermaid diagrams must use camelCase or underscore node IDs.
- Output ONLY Markdown.
"""

OVERVIEW_USER_PROMPT = """\
## Repository: {repo_name}

## Repository Statistics
- Total files: {total_files}
- Total components: {total_components}
- Languages: {languages}

## Module Tree
```
{module_tree_summary}
```

## Module Documentation Summaries

{module_summaries}

Generate the top-level repository overview documentation.
"""


def format_source_blocks(components: list, language_map: dict[str, str] | None = None) -> str:
    """Format component source code into fenced code blocks for the prompt."""
    blocks = []
    for comp in components:
        lang = EXTENSION_TO_LANG.get(comp.language, comp.language)
        header = f"### {comp.component_type}: `{comp.qualified_name}` ({comp.relative_path}:{comp.start_line}-{comp.end_line})"
        code_block = f"```{lang}\n{comp.code_snippet}\n```"
        blocks.append(f"{header}\n\n{code_block}")
    return "\n\n---\n\n".join(blocks)
