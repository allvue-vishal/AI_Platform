"""Text classification benchmark tasks."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class ClassificationBenchmark(BaseBenchmark):
    name = "Classification"
    category = "Classification"
    description = "Sentiment analysis, document type classification, news categorization, and fraud detection."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="cls_01",
                prompt=(
                    "Classify the earnings sentiment as 'bullish', 'bearish', or 'neutral'. "
                    "Reply with one word only.\n\n"
                    "Q3 revenue surged 25% YoY, beating consensus by $200M. Management "
                    "raised full-year guidance and announced a $5B share buyback program."
                ),
                expected_answer="bullish",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="cls_02",
                prompt=(
                    "Classify the earnings sentiment as 'bullish', 'bearish', or 'neutral'. "
                    "Reply with one word only.\n\n"
                    "The company reported a $2.3B write-down on goodwill impairment, cut "
                    "its dividend by 50%, and announced a 15% workforce reduction amid "
                    "declining demand."
                ),
                expected_answer="bearish",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="cls_03",
                prompt=(
                    "Classify the earnings sentiment as 'bullish', 'bearish', or 'neutral'. "
                    "Reply with one word only.\n\n"
                    "Revenue came in line with expectations at $4.2B. Management maintained "
                    "existing guidance and reiterated its long-term growth targets without "
                    "any changes to capital allocation plans."
                ),
                expected_answer="neutral",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="cls_04",
                prompt=(
                    "Classify this financial news into one category: 'M&A', 'macro', "
                    "'regulatory', 'earnings', or 'IPO'. Reply with one word or phrase only.\n\n"
                    "GlobalTech Inc. has agreed to acquire DataStream Corp. for $12.5 billion "
                    "in a cash-and-stock deal, creating the largest cloud infrastructure "
                    "provider in the sector."
                ),
                expected_answer="m&a",
                eval_method=EvalMethod.EXACT_MATCH,
                eval_criteria={"alternatives": ["M&A", "m&a", "merger", "acquisition"]},
            ),
            BenchmarkTask(
                task_id="cls_05",
                prompt=(
                    "Classify this financial news into one category: 'M&A', 'macro', "
                    "'regulatory', 'earnings', or 'IPO'. Reply with one word only.\n\n"
                    "The Federal Reserve raised the benchmark interest rate by 25 basis "
                    "points, signaling that further tightening may be necessary to combat "
                    "persistent inflationary pressures in the services sector."
                ),
                expected_answer="macro",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="cls_06",
                prompt=(
                    "Classify this SEC filing type as '10-K', '10-Q', '8-K', 'S-1', or "
                    "'13F'. Reply with just the form type.\n\n"
                    "The document contains the company's quarterly financial statements "
                    "for the three months ended September 30, including condensed "
                    "consolidated balance sheet and income statement, along with MD&A "
                    "discussing quarterly performance."
                ),
                expected_answer="10-Q",
                eval_method=EvalMethod.EXACT_MATCH,
                eval_criteria={"alternatives": ["10-q", "10Q"]},
            ),
            BenchmarkTask(
                task_id="cls_07",
                prompt=(
                    "Classify the intent as 'buy', 'sell', 'hold', 'research', or "
                    "'compliance'. Reply with one word only.\n\n"
                    "I want to liquidate our entire position in XYZ Corp before the "
                    "lockup period expires next week."
                ),
                expected_answer="sell",
                eval_method=EvalMethod.EXACT_MATCH,
                eval_criteria={"alternatives": ["liquidate"]},
            ),
            BenchmarkTask(
                task_id="cls_08",
                prompt=(
                    "Classify this transaction as 'suspicious' or 'normal'. Reply with "
                    "one word only.\n\n"
                    "A newly opened corporate account received a $2.1M wire transfer from "
                    "an offshore shell company in the Cayman Islands, immediately followed "
                    "by 47 outbound wire transfers to different accounts across 8 countries, "
                    "all within 24 hours."
                ),
                expected_answer="suspicious",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        response_clean = response.strip().lower().rstrip(".")
        expected = task.expected_answer.lower()

        if expected in response_clean:
            return 100.0

        alternatives = task.eval_criteria.get("alternatives", [])
        for alt in alternatives:
            if alt.lower() in response_clean:
                return 100.0

        return 0.0
