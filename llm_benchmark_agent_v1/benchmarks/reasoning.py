"""Reasoning and logic benchmark tasks."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class ReasoningBenchmark(BaseBenchmark):
    name = "Reasoning"
    category = "Reasoning"
    description = "Logical deduction, syllogisms, incentive logic, and return math traps."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="reason_01",
                prompt=(
                    "All hedge funds are pooled investment vehicles. Some pooled investment "
                    "vehicles are registered with the SEC. Can we conclude that some hedge "
                    "funds are registered with the SEC? Answer only 'Yes' or 'No'."
                ),
                expected_answer="No",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="reason_02",
                prompt=(
                    "If interest rates rise, bond prices fall. Bond prices just fell. "
                    "Did interest rates rise? Answer only 'Not necessarily', 'Yes', or 'No'."
                ),
                expected_answer="Not necessarily",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="reason_03",
                prompt=(
                    "A portfolio has 10 stocks. If you sell all but 3, how many stocks "
                    "remain in the portfolio? Answer with just the number."
                ),
                expected_answer="3",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="reason_04",
                prompt=(
                    "A fund manager claims: 'Our fund returned 20% in Year 1 and lost 20% "
                    "in Year 2, so over two years we broke even.' Explain why this is "
                    "incorrect in 2-3 sentences."
                ),
                expected_answer="net loss",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(net loss|less than|96|4%|not break even|does not cancel|multiplicative|0\.96)"
                },
            ),
            BenchmarkTask(
                task_id="reason_05",
                prompt=(
                    "A company's P/E ratio is 15 and its EPS is $4. A competitor has a P/E "
                    "of 20 and EPS of $3. Which company has the higher stock price and what "
                    "is it? Answer concisely."
                ),
                expected_answer="60",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={"pattern": r"(?i)(60|competitor|second)"},
            ),
            BenchmarkTask(
                task_id="reason_06",
                prompt=(
                    "An LP invests in a fund with a 2% management fee and 20% carried "
                    "interest above an 8% hurdle rate. If the fund returns exactly 8%, "
                    "does the GP receive any carried interest? Answer 'Yes' or 'No' and "
                    "explain briefly."
                ),
                expected_answer="No",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={"pattern": r"(?i)(no|zero|does not|doesn.t)"},
            ),
            BenchmarkTask(
                task_id="reason_07",
                prompt=(
                    "A portfolio is 60% stocks and 40% bonds. Stocks return 10% and bonds "
                    "return 4%. What is the portfolio return? Show your calculation."
                ),
                expected_answer="7.6",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={"pattern": r"7\.6"},
            ),
            BenchmarkTask(
                task_id="reason_08",
                prompt=(
                    "Company A has a debt-to-equity ratio of 0.5. Company B has a ratio "
                    "of 2.0. Company C has a ratio of 1.0. Which company is the most "
                    "leveraged? Answer with just the letter."
                ),
                expected_answer="B",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        import re

        response_clean = response.strip()

        if task.eval_method == EvalMethod.EXACT_MATCH:
            return 100.0 if task.expected_answer.lower() in response_clean.lower() else 0.0

        if task.eval_method == EvalMethod.NUMERIC_MATCH:
            numbers = re.findall(r"\d+", response_clean)
            return 100.0 if task.expected_answer in numbers else 0.0

        if task.eval_method == EvalMethod.REGEX_MATCH:
            pattern = task.eval_criteria.get("pattern", "")
            return 100.0 if re.search(pattern, response_clean) else 0.0

        return 0.0
