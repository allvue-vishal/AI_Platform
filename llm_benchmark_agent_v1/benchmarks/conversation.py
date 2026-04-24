"""Multi-turn conversation benchmark tasks."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod


class ConversationBenchmark(BaseBenchmark):
    name = "Conversation"
    category = "Conversation"
    description = "Multi-turn dialogue: portfolio advice, due diligence, risk discussions."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="conv_01",
                prompt="",
                conversation_turns=[
                    [{"role": "user", "content": "I'm 35 years old with $200K to invest for retirement. I have moderate risk tolerance. What asset allocation would you recommend?"}],
                    [{"role": "user", "content": "That sounds reasonable. But what if I wanted to tilt more toward growth? How would the allocation change?"}],
                    [{"role": "user", "content": "How should I rebalance this portfolio and how often?"}],
                ],
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) Financial accuracy of allocation advice, "
                        "(2) Context retention - remembers age, amount, risk tolerance, "
                        "(3) Practical and actionable rebalancing guidance, "
                        "(4) Consistency across turns"
                    ),
                },
            ),
            BenchmarkTask(
                task_id="conv_02",
                prompt="",
                conversation_turns=[
                    [{"role": "user", "content": "I'm an LP evaluating a PE fund. Fund VII has a net IRR of 22% and 2.1x MOIC. How does this compare to industry benchmarks?"}],
                    [{"role": "user", "content": "The fund has 3 portfolio companies. One of them is a SaaS business growing at 40% YoY. What questions should I ask about this company during due diligence?"}],
                    [{"role": "user", "content": "What about the exit timeline? The fund is in year 4 of a 10-year life. What should I expect?"}],
                ],
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) PE knowledge accuracy, "
                        "(2) Quality of due diligence questions, "
                        "(3) Context continuity across turns, "
                        "(4) Realistic expectations about fund lifecycle"
                    ),
                },
            ),
            BenchmarkTask(
                task_id="conv_03",
                prompt="",
                conversation_turns=[
                    [{"role": "user", "content": "The market just dropped 10% in a week. I'm worried about my $1M equity portfolio. What hedging strategies should I consider?"}],
                    [{"role": "user", "content": "Tell me more about using put options as portfolio insurance. How would that work specifically?"}],
                    [{"role": "user", "content": "What would that cost me approximately? Is it worth the protection?"}],
                ],
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) Hedging strategy knowledge, "
                        "(2) Practical options explanation, "
                        "(3) Honest cost/benefit analysis, "
                        "(4) Remembers portfolio size and concern from first message"
                    ),
                },
            ),
            BenchmarkTask(
                task_id="conv_04",
                prompt="",
                conversation_turns=[
                    [{"role": "user", "content": "My name is Sarah. I'm a CFO at a mid-cap manufacturing company and we need to hedge our EUR/USD exposure of about 50 million euros over the next 12 months."}],
                    [{"role": "user", "content": "What are the pros and cons of forward contracts vs options for our situation?"}],
                    [{"role": "user", "content": "Thanks for the analysis. By the way, what's my name and role, and how much exposure are we hedging?"}],
                ],
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) Memory - recalls Sarah, CFO, 50M EUR, "
                        "(2) FX hedging knowledge, "
                        "(3) Tailored advice for a corporate CFO context, "
                        "(4) Clear pros/cons comparison"
                    ),
                },
            ),
            BenchmarkTask(
                task_id="conv_05",
                prompt="",
                conversation_turns=[
                    [{"role": "user", "content": "I want to invest $500K. I'm conservative, retiring in 15 years, and I absolutely do not want any cryptocurrency or speculative assets in my portfolio."}],
                    [{"role": "user", "content": "That sounds good. Can you give me a specific allocation with percentages and example ETFs?"}],
                    [{"role": "user", "content": "Wait - does this portfolio include any cryptocurrency or speculative positions? I said no crypto."}],
                ],
                eval_method=EvalMethod.LLM_JUDGE,
                eval_criteria={
                    "rubric": (
                        "Rate 1-10 on: (1) Constraint adherence - no crypto throughout, "
                        "(2) Conservative allocation appropriate for 15-year horizon, "
                        "(3) Specific ETF recommendations, "
                        "(4) Reassurance and memory of constraints in final turn"
                    ),
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        if not response.strip():
            return 0.0
        return 50.0
