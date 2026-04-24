"""Document summarization benchmark tasks."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class SummarizationBenchmark(BaseBenchmark):
    name = "Summarization"
    category = "Summarization"
    description = "Summarizing earnings calls, 10-K filings, fund letters, and credit memos."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="summ_01",
                prompt=(
                    "Summarize the following earnings call excerpt in 2-3 sentences:\n\n"
                    "Good morning everyone. In Q3 2024, our revenue grew 18% year-over-year "
                    "to $4.2 billion, driven by strong demand in our cloud services division "
                    "which saw 32% growth. However, operating margins compressed by 200 basis "
                    "points to 22% due to increased R&D spending and higher employee costs "
                    "from our recent acquisitions. We are revising our full-year guidance "
                    "downward by 3%, now expecting revenue of $16.5 billion, primarily due "
                    "to softening enterprise demand in Europe and currency headwinds. Our "
                    "free cash flow remained robust at $890 million, and we returned $500 "
                    "million to shareholders through buybacks during the quarter."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) Faithfulness to the source, "
                        "(2) Conciseness, (3) Coverage of key financials "
                        "(revenue growth, margin compression, guidance revision)."
                    ),
                    "key_points": [
                        "revenue", "18%", "margin", "guidance", "year-over-year",
                    ],
                },
            ),
            BenchmarkTask(
                task_id="summ_02",
                prompt=(
                    "Summarize this 10-K risk factor in 2-3 sentences:\n\n"
                    "Our operations are subject to increasing cybersecurity threats that "
                    "could result in unauthorized access to sensitive client financial data. "
                    "A significant data breach could expose us to regulatory penalties under "
                    "the Gramm-Leach-Bliley Act and state privacy laws, result in class-action "
                    "litigation, and damage our reputation with institutional investors. We "
                    "have invested $120 million in cybersecurity infrastructure over the past "
                    "two years, but the evolving nature of threats means we cannot guarantee "
                    "that our defenses will prevent all intrusions. Insurance coverage may not "
                    "be sufficient to cover all losses from a major incident, and the financial "
                    "impact could be material to our operations."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on faithfulness, conciseness, and coverage "
                        "of the key risk dimensions."
                    ),
                    "key_points": [
                        "cybersecurity", "data breach", "regulatory", "financial impact",
                    ],
                },
            ),
            BenchmarkTask(
                task_id="summ_03",
                prompt=(
                    "Provide a one-paragraph summary of this PE fund quarterly letter:\n\n"
                    "Dear Limited Partners, Fund VII generated a net IRR of 18.2% and a "
                    "1.6x MOIC through Q3 2024. During the quarter, we successfully exited "
                    "our position in MedTech Solutions at a 3.2x return through a strategic "
                    "sale to a Fortune 500 acquirer. We deployed $85 million into two new "
                    "platform investments: a B2B SaaS company serving the insurance industry "
                    "and a specialty chemicals manufacturer. Portfolio company EBITDA grew "
                    "12% on average across our holdings. We remain cautious on leverage "
                    "given the current rate environment and are focusing on operational "
                    "value creation rather than financial engineering. Total committed "
                    "capital stands at $1.2 billion with 65% called to date."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on faithfulness, conciseness, and coverage "
                        "of fund performance, exits, and new investments."
                    ),
                    "key_points": [
                        "IRR", "MOIC", "exit", "new investment", "EBITDA",
                    ],
                },
            ),
            BenchmarkTask(
                task_id="summ_04",
                prompt=(
                    "Summarize in exactly 3 bullet points:\n\n"
                    "The Federal Open Market Committee decided to maintain the federal funds "
                    "rate at the 5.25-5.50 percent target range. The Committee judges that "
                    "inflation remains somewhat elevated above the 2 percent objective, with "
                    "core PCE running at 2.8% year-over-year. The labor market remains tight "
                    "with unemployment at 3.7%, though job gains have moderated. Economic "
                    "activity expanded at a solid pace in the fourth quarter. The Committee "
                    "remains committed to returning inflation to its 2 percent objective and "
                    "will continue to assess incoming data to determine the appropriate "
                    "stance of monetary policy. Members noted that risks to achieving "
                    "employment and inflation goals are moving into better balance."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on faithfulness, format (3 bullet points), "
                        "and coverage of rates, inflation, and employment."
                    ),
                    "key_points": [
                        "interest rate", "inflation", "employment", "monetary policy",
                    ],
                },
            ),
            BenchmarkTask(
                task_id="summ_05",
                prompt=(
                    "Write a one-sentence TL;DR for this credit memo:\n\n"
                    "AcmeCorp (Ba2/BB+) is seeking a $250M senior secured term loan to "
                    "refinance existing debt and fund a bolt-on acquisition. The company's "
                    "leverage stands at 4.5x net debt/EBITDA, above the industry median of "
                    "3.2x. Free cash flow generation is adequate at $45M annually, providing "
                    "1.8x interest coverage. Key risks include customer concentration (top 3 "
                    "clients represent 55% of revenue) and exposure to cyclical end markets. "
                    "We recommend approval with a covenant package requiring leverage below "
                    "5.0x and minimum liquidity of $30M."
                ),
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on faithfulness, brevity (one sentence), "
                        "and informativeness."
                    ),
                    "key_points": [
                        "credit", "leverage", "cash flow", "covenant",
                    ],
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        if not response.strip():
            return 0.0
        key_points = task.eval_criteria.get("key_points", [])
        if not key_points:
            return 50.0
        hits = sum(1 for kp in key_points if kp.lower() in response.lower())
        return round((hits / len(key_points)) * 100, 1)
