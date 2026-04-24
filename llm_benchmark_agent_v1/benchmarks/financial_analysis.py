"""Analysis benchmark tasks -- valuation, modeling, ratios, and deal analysis."""

from __future__ import annotations

import re

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class FinancialAnalysisBenchmark(BaseBenchmark):
    name = "Analysis"
    category = "Analysis"
    description = "DCF valuation, ratio analysis, LBO modeling, and deal structuring."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="fa_01",
                prompt=(
                    "A company has EBITDA of $50M, an EV/EBITDA multiple of 10x, "
                    "net debt of $120M, and 10M shares outstanding. What is the "
                    "implied share price? Show your calculation."
                ),
                expected_answer="38",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={"pattern": r"(?:38|37\.?\d*|38\.0)"},
            ),
            BenchmarkTask(
                task_id="fa_02",
                prompt=(
                    "A company has the following: Revenue $200M, COGS $120M, "
                    "SG&A $30M, D&A $10M, Interest $5M, Tax rate 25%. "
                    "Calculate: (a) Gross Margin %, (b) EBITDA, (c) Net Income."
                ),
                expected_answer="Gross Margin 40%, EBITDA $50M, Net Income $26.25M",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(40%|40\s*percent).*?(50|50M).*?(26\.25|26,250)"
                },
            ),
            BenchmarkTask(
                task_id="fa_03",
                prompt=(
                    "In a simplified LBO, a PE firm acquires a company for $500M "
                    "using 60% debt and 40% equity. After 5 years, EBITDA has grown "
                    "from $50M to $75M and the exit multiple is the same 10x. All "
                    "debt has been repaid. What is the equity return multiple (MOIC) "
                    "and approximate IRR? Show your work."
                ),
                expected_answer="3.75x MOIC, ~30% IRR",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(3\.75|3\.7\d).*?(IRR|internal rate)"
                },
            ),
            BenchmarkTask(
                task_id="fa_04",
                prompt=(
                    "Calculate the Weighted Average Cost of Capital (WACC) given: "
                    "Equity market value $600M, Debt market value $400M, Cost of "
                    "equity 12%, Pre-tax cost of debt 6%, Tax rate 25%. "
                    "Give the answer as a percentage to one decimal place."
                ),
                expected_answer="9.0",
                eval_method=EvalMethod.NUMERIC_MATCH,
                eval_criteria={"tolerance": 0.2},
            ),
            BenchmarkTask(
                task_id="fa_05",
                prompt=(
                    "A company has: Current Assets $150M, Current Liabilities $90M, "
                    "Inventory $40M, Cash $30M. Calculate the following three ratios: "
                    "(a) Current Ratio, (b) Quick Ratio, (c) Cash Ratio."
                ),
                expected_answer="Current Ratio 1.67, Quick Ratio 1.22, Cash Ratio 0.33",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(1\.6[67]|1\.7).*?(1\.2[12]|1\.22).*?(0\.33|0\.3)"
                },
            ),
            BenchmarkTask(
                task_id="fa_06",
                prompt=(
                    "Explain the three main approaches to business valuation in "
                    "2-3 sentences each: (1) Discounted Cash Flow, (2) Comparable "
                    "Company Analysis, and (3) Precedent Transactions."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on accuracy of describing DCF (present value of "
                        "future cash flows), Comps (market multiples of similar firms), "
                        "and Precedent Transactions (historical M&A deal multiples)."
                    ),
                },
            ),
            BenchmarkTask(
                task_id="fa_07",
                prompt=(
                    "A company's free cash flows are projected as: Year 1: $10M, "
                    "Year 2: $12M, Year 3: $14M, Year 4: $16M, Year 5: $18M. "
                    "Terminal growth rate is 3% and WACC is 10%. Calculate the "
                    "enterprise value using a DCF model (with a terminal value "
                    "based on the Gordon Growth Model). Round to the nearest million."
                ),
                expected_answer="265",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(26[0-9]|27[0-5])"
                },
            ),
            BenchmarkTask(
                task_id="fa_08",
                prompt=(
                    "An investor is deciding between two deals:\n"
                    "Deal A: Invest $10M, receive $2M/year for 7 years\n"
                    "Deal B: Invest $10M, receive nothing for 4 years, then $5M/year for 3 years\n"
                    "At a 10% discount rate, which deal has a higher NPV? "
                    "Show the NPV of each deal."
                ),
                expected_answer="Deal A",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)deal\s*a"
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        response_clean = response.strip()

        if task.eval_method == EvalMethod.EXACT_MATCH:
            return 100.0 if task.expected_answer.lower() in response_clean.lower() else 0.0

        if task.eval_method == EvalMethod.NUMERIC_MATCH:
            numbers = re.findall(r"[\d,]+\.?\d*", response_clean.replace(",", ""))
            expected = float(task.expected_answer)
            tolerance = task.eval_criteria.get("tolerance", 0.5)
            for num_str in numbers:
                try:
                    if abs(float(num_str) - expected) <= tolerance:
                        return 100.0
                except ValueError:
                    continue
            return 0.0

        if task.eval_method == EvalMethod.REGEX_MATCH:
            pattern = task.eval_criteria.get("pattern", "")
            return 100.0 if re.search(pattern, response_clean) else 0.0

        if task.eval_method == EvalMethod.LLM_JUDGE:
            return 50.0

        return 0.0
