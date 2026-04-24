"""Auto-discovers and registers all benchmark implementations."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark
from benchmarks.code_generation import CodeGenerationBenchmark
from benchmarks.reasoning import ReasoningBenchmark
from benchmarks.math_bench import MathBenchmark
from benchmarks.summarization import SummarizationBenchmark
from benchmarks.classification import ClassificationBenchmark
from benchmarks.conversation import ConversationBenchmark
from benchmarks.knowledge_qa import KnowledgeQABenchmark
from benchmarks.tool_use import ToolUseBenchmark
from benchmarks.financial_analysis import FinancialAnalysisBenchmark
from benchmarks.regulatory_compliance import RegulatoryComplianceBenchmark

ALL_BENCHMARKS: list[BaseBenchmark] = [
    CodeGenerationBenchmark(),
    ReasoningBenchmark(),
    MathBenchmark(),
    SummarizationBenchmark(),
    ClassificationBenchmark(),
    ConversationBenchmark(),
    KnowledgeQABenchmark(),
    ToolUseBenchmark(),
    FinancialAnalysisBenchmark(),
    RegulatoryComplianceBenchmark(),
]

CATEGORY_SLUG_MAP: dict[str, str] = {}
for _b in ALL_BENCHMARKS:
    slug = _b.category.lower().replace(" ", "_").replace("/", "_").replace("&", "and")
    CATEGORY_SLUG_MAP[slug] = _b.category
    short = slug.split("_")[0]
    if short not in CATEGORY_SLUG_MAP:
        CATEGORY_SLUG_MAP[short] = _b.category


def get_benchmark_by_category(category: str) -> BaseBenchmark | None:
    target = CATEGORY_SLUG_MAP.get(category.lower(), category)
    for b in ALL_BENCHMARKS:
        if b.category.lower() == target.lower():
            return b
    return None


def get_all_categories() -> list[str]:
    return [b.category for b in ALL_BENCHMARKS]
