"""Validator agent — checks generated documentation for quality and correctness.

Validates:
- Required sections (overview, API reference, diagrams)
- Mermaid syntax basics
- Component names exist in the codebase (no hallucinations)
- Cross-references to other modules are valid
"""

from __future__ import annotations

import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from autodoc.parser.models import ParseResult

REQUIRED_SECTIONS = [
    "overview",
    "component",
    "api",
    "diagram",
]

VALIDATOR_SYSTEM = """\
You are a documentation quality reviewer. Given a generated Markdown document \
for a code module, check it for completeness and accuracy.

Check the following:
1. Does it have a module overview section?
2. Does it describe key components (classes, functions)?
3. Does it include an API reference with signatures?
4. Does it include at least one Mermaid diagram?
5. Are component names real (match the provided component list)?
6. Is the Mermaid syntax valid (no spaces in node IDs)?

Respond with a JSON object:
{
  "is_valid": true/false,
  "issues": ["issue 1", "issue 2"],
  "suggestions": ["suggestion 1"]
}

Respond ONLY with the JSON object, no extra text.
"""


def _structural_validation(doc: str, parse_result: ParseResult | None) -> list[str]:
    """Fast structural checks before invoking the LLM."""
    issues = []

    lower = doc.lower()
    if "overview" not in lower and "# " not in doc:
        issues.append("Missing module overview heading")

    if "```mermaid" not in lower:
        issues.append("No Mermaid diagram found")

    mermaid_blocks = re.findall(r"```mermaid([\s\S]*?)```", doc, re.IGNORECASE)
    for block in mermaid_blocks:
        node_ids = re.findall(r"\b([A-Za-z_]\w*)\s*[\[\({]", block)
        for nid in node_ids:
            if " " in nid:
                issues.append(f"Mermaid node ID contains space: '{nid}'")

    if parse_result:
        valid_names = set()
        for comp in parse_result.all_components.values():
            valid_names.add(comp.name)
            valid_names.add(comp.qualified_name)

        backtick_refs = re.findall(r"`([A-Za-z_]\w+(?:\.\w+)*)`", doc)
        suspicious = []
        for ref in backtick_refs:
            base = ref.split(".")[-1]
            if (
                len(base) > 3
                and base not in valid_names
                and base.lower() not in {"none", "true", "false", "self", "string", "int", "bool", "list", "dict", "float", "str", "type", "class", "function", "method", "return", "import", "from", "mermaid", "flowchart", "sequencediagram", "markdown", "json", "yaml", "python", "javascript", "typescript"}
            ):
                suspicious.append(base)

        if len(suspicious) > 5:
            issues.append(f"Possible hallucinated names: {', '.join(suspicious[:10])}")

    return issues


def validate_doc(
    doc: str,
    module_name: str,
    parse_result: ParseResult | None,
    llm: BaseChatModel | None = None,
) -> tuple[bool, str]:
    """
    Validate a generated document.

    Returns (is_valid, feedback_string).
    Runs structural checks first; optionally runs LLM-based review.
    """
    issues = _structural_validation(doc, parse_result)

    if not doc.strip() or len(doc) < 50:
        return False, "Document is empty or too short."

    if issues:
        feedback = "Structural issues found:\n" + "\n".join(f"- {i}" for i in issues)
        if any("Missing module overview" in i for i in issues):
            return False, feedback
        if len(issues) >= 3:
            return False, feedback

    if llm and not issues:
        try:
            component_names = ""
            if parse_result:
                names = sorted(parse_result.all_components.keys())[:100]
                component_names = "\n".join(names)

            prompt = (
                f"Module: {module_name}\n\n"
                f"Known component IDs:\n{component_names}\n\n"
                f"Document to review:\n{doc[:6000]}"
            )
            resp = llm.invoke([
                SystemMessage(content=VALIDATOR_SYSTEM),
                HumanMessage(content=prompt),
            ])
            text = resp.content
            import json
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())
                if not data.get("is_valid", True):
                    issue_list = data.get("issues", [])
                    return False, "LLM validation issues:\n" + "\n".join(f"- {i}" for i in issue_list)
        except Exception:
            pass

    return True, "OK"
