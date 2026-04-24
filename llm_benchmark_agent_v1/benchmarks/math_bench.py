"""Math benchmark tasks."""

from __future__ import annotations

import re

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class MathBenchmark(BaseBenchmark):
    name = "Math"
    category = "Math"
    description = "NPV, IRR, compound interest, WACC, carried interest, and loan calculations."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="math_01",
                prompt=(
                    "An investment costs $50,000 today and generates cash flows of $15,000 "
                    "per year for 4 years. Using a 10% discount rate, what is the NPV? "
                    "Answer with just the number rounded to the nearest dollar."
                ),
                expected_answer="-2451",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_02",
                prompt=(
                    "You invest $10,000 at 8% annual interest compounded quarterly. "
                    "How much do you have after 5 years? Round to the nearest cent. "
                    "Answer with just the dollar amount."
                ),
                expected_answer="14859.47",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_03",
                prompt=(
                    "A company has 60% equity (cost of equity 12%) and 40% debt "
                    "(cost of debt 6%, tax rate 25%). What is the WACC? "
                    "Answer as a percentage number only (e.g. 9.0)."
                ),
                expected_answer="9.0",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_04",
                prompt=(
                    "A bond has a face value of $1,000, a coupon rate of 5% paid annually, "
                    "and 3 years to maturity. If the yield to maturity is 4%, what is the "
                    "bond price? Round to the nearest cent. Answer with just the number."
                ),
                expected_answer="1027.75",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_05",
                prompt=(
                    "A PE fund has committed capital of $100M. After returning the $100M "
                    "to LPs plus an 8% preferred return ($8M), there is $40M in remaining "
                    "profits. With a 20% carry, how much does the GP receive in carried "
                    "interest? Answer in millions (just the number)."
                ),
                expected_answer="8",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_06",
                prompt=(
                    "What is the monthly payment on a $500,000 mortgage at 6.5% annual "
                    "rate for 30 years? Round to the nearest cent. Answer with just the number."
                ),
                expected_answer="3160.34",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_07",
                prompt=(
                    "An investor buys a stock at $45 and sells at $54, receiving $2.25 "
                    "in dividends during the holding period. What is the total return "
                    "as a percentage? Answer with just the number."
                ),
                expected_answer="25",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="math_08",
                prompt=(
                    "An investment of $1,000 today returns $600 at end of year 1 and "
                    "$600 at end of year 2. What is the approximate IRR? "
                    "Answer as a percentage rounded to 1 decimal place (just the number)."
                ),
                expected_answer="13.1",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        response_clean = response.strip().replace(",", "").replace("$", "").replace("%", "")
        expected = task.expected_answer

        numbers = re.findall(r"-?[\d]+\.?\d*", response_clean)
        if not numbers:
            return 0.0

        for num_str in numbers:
            try:
                if abs(float(num_str) - float(expected)) < max(0.02, abs(float(expected)) * 0.005):
                    return 100.0
            except ValueError:
                continue

        return 0.0
