"""Compliance benchmark tasks -- regulations, AML/KYC, fiduciary duty."""

from __future__ import annotations

import re

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class RegulatoryComplianceBenchmark(BaseBenchmark):
    name = "Compliance"
    category = "Compliance"
    description = "SEC rules, fund regulations, AML/KYC, and fiduciary duty."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="reg_01",
                prompt=(
                    "Under SEC rules, what is the minimum net worth required for an "
                    "individual to qualify as an accredited investor (excluding the "
                    "value of their primary residence)? Answer with just the dollar amount."
                ),
                expected_answer="1000000",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(\$?\s*1[,.]?000[,.]?000|\$?\s*1\s*million|1M)"
                },
            ),
            BenchmarkTask(
                task_id="reg_02",
                prompt=(
                    "What is the difference between a 3(c)(1) fund and a 3(c)(7) fund "
                    "under the Investment Company Act of 1940? Explain in 2-3 sentences."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on accuracy: 3(c)(1) limited to 100 investors with "
                        "no qualification requirements; 3(c)(7) allows unlimited qualified "
                        "purchasers. Must mention both investor limits and qualification."
                    ),
                    "key_points": ["100", "qualified purchaser"],
                },
            ),
            BenchmarkTask(
                task_id="reg_03",
                prompt=(
                    "Under the Dodd-Frank Act, what is the Volcker Rule? Explain in "
                    "2-3 sentences."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on accuracy: Volcker Rule restricts banks from "
                        "proprietary trading and limits investment in hedge/PE funds. "
                        "Named after Paul Volcker."
                    ),
                    "key_points": ["proprietary trading", "bank"],
                },
            ),
            BenchmarkTask(
                task_id="reg_04",
                prompt=(
                    "What are the three main pillars of Anti-Money Laundering (AML) "
                    "compliance that financial institutions must implement? "
                    "List them briefly."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on coverage of: (1) Customer Due Diligence / KYC, "
                        "(2) Transaction Monitoring / Suspicious Activity Reporting, "
                        "(3) Record Keeping / Compliance Program."
                    ),
                    "key_points": ["KYC", "monitoring", "reporting"],
                },
            ),
            BenchmarkTask(
                task_id="reg_05",
                prompt=(
                    "Is a Registered Investment Adviser (RIA) held to a fiduciary "
                    "standard or a suitability standard? Answer with one word: "
                    "'fiduciary' or 'suitability'."
                ),
                expected_answer="fiduciary",
                eval_method=EvalMethod.EXACT_MATCH,
            ),
            BenchmarkTask(
                task_id="reg_06",
                prompt=(
                    "Under SEC Rule 144, what is the general holding period for "
                    "restricted securities of a reporting company before they can "
                    "be resold? Answer with the number of months."
                ),
                expected_answer="6",
                eval_method=EvalMethod.NUMERIC_MATCH,
            ),
            BenchmarkTask(
                task_id="reg_07",
                prompt=(
                    "A hedge fund has 150 US-based investors and $200M in AUM. "
                    "Must it register with the SEC as an investment adviser under "
                    "the Advisers Act? Answer 'Yes' or 'No' and explain briefly "
                    "why (consider the $150M AUM threshold)."
                ),
                expected_answer="Yes",
                eval_method=EvalMethod.REGEX_MATCH,
                eval_criteria={
                    "pattern": r"(?i)(yes|must register|required to register)"
                },
            ),
            BenchmarkTask(
                task_id="reg_08",
                prompt=(
                    "Explain the difference between Regulation D Rule 506(b) and "
                    "Rule 506(c) for private placements. Be concise."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10: 506(b) allows up to 35 non-accredited but "
                        "no general solicitation; 506(c) allows general solicitation "
                        "but all investors must be verified accredited."
                    ),
                    "key_points": ["solicitation", "accredited"],
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        response_clean = response.strip()

        if task.eval_method == EvalMethod.EXACT_MATCH:
            return 100.0 if task.expected_answer.lower() in response_clean.lower() else 0.0

        if task.eval_method == EvalMethod.NUMERIC_MATCH:
            numbers = re.findall(r"\d+", response_clean)
            return 100.0 if task.expected_answer in numbers else 0.0

        if task.eval_method == EvalMethod.REGEX_MATCH:
            pattern = task.eval_criteria.get("pattern", "")
            return 100.0 if re.search(pattern, response_clean) else 0.0

        if task.eval_method == EvalMethod.LLM_JUDGE:
            key_points = task.eval_criteria.get("key_points", [])
            if not key_points:
                return 50.0
            hits = sum(1 for kp in key_points if kp.lower() in response_clean.lower())
            return round((hits / len(key_points)) * 100, 1)

        return 0.0
