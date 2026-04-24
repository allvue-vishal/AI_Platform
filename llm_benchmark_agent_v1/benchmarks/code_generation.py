"""Financial code generation benchmark tasks."""

from __future__ import annotations

import re
import textwrap

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class CodeGenerationBenchmark(BaseBenchmark):
    name = "Coding"
    category = "Coding"
    description = "Python code generation: returns calculation, risk metrics, amortization schedules."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="code_01",
                prompt=(
                    "Write a Python function `portfolio_return(prices)` that takes a list of "
                    "daily portfolio prices and returns the total return as a decimal. "
                    "Example: portfolio_return([100, 110]) returns 0.1. Only output the function."
                ),
                expected_answer="portfolio_return",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "round(portfolio_return([100, 110]), 4)", "expected": 0.1},
                        {"call": "round(portfolio_return([100, 100]), 4)", "expected": 0.0},
                        {"call": "round(portfolio_return([200, 220, 210, 230]), 4)", "expected": 0.15},
                        {"call": "round(portfolio_return([50, 45]), 4)", "expected": -0.1},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_02",
                prompt=(
                    "Write a Python function `sharpe_ratio(returns, risk_free_rate)` that "
                    "computes the Sharpe ratio given a list of period returns and a per-period "
                    "risk-free rate. Sharpe = mean(excess returns) / std(excess returns). "
                    "Use sample standard deviation. Only output the function."
                ),
                expected_answer="sharpe_ratio",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "abs(sharpe_ratio([0.01, 0.02, -0.01, 0.03, 0.01], 0.001) - 0.9267) < 0.1", "expected": True},
                        {"call": "abs(sharpe_ratio([0.05, 0.05, 0.05], 0.01) - float('inf')) == 0 or abs(sharpe_ratio([0.05, 0.05, 0.05], 0.01)) > 100", "expected": True},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_03",
                prompt=(
                    "Write a Python function `loan_payment(principal, annual_rate, years)` that "
                    "returns the fixed monthly payment for a fully amortizing loan, rounded to "
                    "2 decimal places. Formula: M = P * r*(1+r)^n / ((1+r)^n - 1) where "
                    "r = annual_rate/12, n = years*12. Only output the function."
                ),
                expected_answer="loan_payment",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "loan_payment(200000, 0.06, 30)", "expected": 1199.10},
                        {"call": "loan_payment(100000, 0.05, 15)", "expected": 790.79},
                        {"call": "loan_payment(500000, 0.065, 30)", "expected": 3160.34},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_04",
                prompt=(
                    "Write a Python function `compound_interest(principal, rate, years, n)` "
                    "that returns the final amount with compound interest, rounded to 2 decimals. "
                    "Formula: A = principal * (1 + rate/n)^(n*years). Only output the function."
                ),
                expected_answer="compound_interest",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "compound_interest(1000, 0.05, 3, 1)", "expected": 1157.63},
                        {"call": "compound_interest(1000, 0.12, 1, 12)", "expected": 1126.83},
                        {"call": "compound_interest(10000, 0.08, 5, 4)", "expected": 14859.47},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_05",
                prompt=(
                    "Write a Python function `moving_average(prices, window)` that returns a "
                    "list of simple moving averages. The output length should be "
                    "len(prices) - window + 1. Only output the function."
                ),
                expected_answer="moving_average",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "moving_average([10, 20, 30, 40, 50], 3)", "expected": [20.0, 30.0, 40.0]},
                        {"call": "moving_average([100, 200, 300], 2)", "expected": [150.0, 250.0]},
                        {"call": "moving_average([5, 5, 5, 5], 1)", "expected": [5.0, 5.0, 5.0, 5.0]},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_06",
                prompt=(
                    "Write a Python function `max_drawdown(prices)` that returns the maximum "
                    "drawdown as a negative decimal. Max drawdown is the largest peak-to-trough "
                    "decline. Example: max_drawdown([100, 120, 90, 110]) returns -0.25 "
                    "(from 120 to 90). Only output the function."
                ),
                expected_answer="max_drawdown",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "abs(max_drawdown([100, 120, 90, 110, 80]) - (-1/3)) < 0.01", "expected": True},
                        {"call": "max_drawdown([100, 110, 120, 130])", "expected": 0.0},
                        {"call": "abs(max_drawdown([100, 120, 90, 110]) - (-0.25)) < 0.01", "expected": True},
                    ]
                },
            ),
            BenchmarkTask(
                task_id="code_07",
                prompt=(
                    "Write a Python function `cagr(begin_value, end_value, years)` that "
                    "returns the compound annual growth rate as a decimal, rounded to 5 "
                    "decimal places. Formula: (end/begin)^(1/years) - 1. Only output the function."
                ),
                expected_answer="cagr",
                eval_method=EvalMethod.CODE_EXECUTION,
                eval_criteria={
                    "test_cases": [
                        {"call": "abs(cagr(100, 200, 10) - 0.07177) < 0.001", "expected": True},
                        {"call": "abs(cagr(1000, 1500, 5) - 0.08447) < 0.001", "expected": True},
                        {"call": "cagr(100, 100, 5)", "expected": 0.0},
                    ]
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        """Extract code from response and run test cases."""
        code = _extract_python_code(response)
        if not code:
            return 0.0

        test_cases = task.eval_criteria.get("test_cases", [])
        if not test_cases:
            return 0.0

        passed = 0
        for tc in test_cases:
            try:
                namespace: dict = {}
                exec(code, namespace)
                result = eval(tc["call"], namespace)
                if result == tc["expected"]:
                    passed += 1
            except Exception:
                continue

        return round((passed / len(test_cases)) * 100, 1)


def _extract_python_code(text: str) -> str:
    """Pull Python code from markdown fences or raw text."""
    pattern = r"```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = [l for l in text.strip().split("\n") if not l.startswith("```")]
    return "\n".join(lines)
