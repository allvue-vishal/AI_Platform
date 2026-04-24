"""Knowledge question-answering benchmark tasks."""

from __future__ import annotations

import re

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class KnowledgeQABenchmark(BaseBenchmark):
    name = "Knowledge"
    category = "Knowledge"
    description = "Factual knowledge: fund structures, regulations, valuation concepts."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="kqa_01",
                prompt="What does IRR stand for in finance? Answer with the full phrase only.",
                expected_answer="Internal Rate of Return",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_02",
                prompt=(
                    "What is the standard management fee percentage for most private "
                    "equity funds? Answer with just the number."
                ),
                expected_answer="2",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_03",
                prompt=(
                    "Under GAAP, which financial statement reports a company's assets, "
                    "liabilities, and shareholders' equity at a point in time? "
                    "Answer with just the name."
                ),
                expected_answer="balance sheet",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_04",
                prompt=(
                    "What SEC form must public companies file annually with audited "
                    "financial statements? Answer with just the form number."
                ),
                expected_answer="10-K",
                eval_method=EvalMethod.EXACT_MATCH,
                eval_criteria={"alternatives": ["10-k", "10K"]},
            ),
            BenchmarkTask(
                task_id="kqa_05",
                prompt=(
                    "In a typical PE fund structure, what is the standard carried "
                    "interest percentage? Answer with just the number."
                ),
                expected_answer="20",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_06",
                prompt="What does LP stand for in fund investing? Answer with the full phrase only.",
                expected_answer="Limited Partner",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_07",
                prompt=(
                    "What financial ratio is calculated as Net Income divided by "
                    "Shareholders' Equity? Answer with the ratio name."
                ),
                expected_answer="Return on Equity",
                eval_method=EvalMethod.EXACT_MATCH,
                eval_criteria={"alternatives": ["ROE", "roe"]},
            ),
            BenchmarkTask(
                task_id="kqa_08",
                prompt="What does EBITDA stand for? Answer with the full phrase only.",
                expected_answer="Earnings Before Interest, Taxes, Depreciation, and Amortization",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)earnings\s+before\s+interest.*tax.*depreciation.*amortization"
                },
            ),
            BenchmarkTask(
                task_id="kqa_09",
                prompt=(
                    "How many members does the Federal Reserve's Board of Governors "
                    "have? Answer with just the number."
                ),
                expected_answer="7",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="kqa_10",
                prompt=(
                    "What is the standard hurdle rate in most PE fund agreements? "
                    "Answer as a percentage (just the number)."
                ),
                expected_answer="8",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        response_clean = response.strip()

        if task.eval_method == EvalMethod.EXACT_MATCH:
            if task.expected_answer.lower() in response_clean.lower():
                return 100.0
            for alt in task.eval_criteria.get("alternatives", []):
                if alt.lower() in response_clean.lower():
                    return 100.0
            return 0.0

        if task.eval_method == EvalMethod.NUMERIC_MATCH:
            numbers = re.findall(r"[\d,]+\.?\d*", response_clean.replace(",", ""))
            expected = task.expected_answer.replace(",", "")
            for num_str in numbers:
                try:
                    if abs(float(num_str) - float(expected)) < 1:
                        return 100.0
                except ValueError:
                    continue
            return 0.0

        if task.eval_method == EvalMethod.REGEX_MATCH:
            pattern = task.eval_criteria.get("pattern", "")
            return 100.0 if re.search(pattern, response_clean) else 0.0

        return 0.0
