"""Financial tool use / function calling benchmark tasks."""

from __future__ import annotations

import json

from benchmarks.base import BaseBenchmark, BenchmarkTask, EvalMethod

STOCK_QUOTE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_stock_quote",
        "description": "Get the current stock price and basic market data for a ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. AAPL"},
                "exchange": {
                    "type": "string",
                    "description": "Stock exchange (optional)",
                },
            },
            "required": ["symbol"],
        },
    },
}

PORTFOLIO_RISK_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_portfolio_risk",
        "description": "Calculate risk metrics for a given portfolio allocation.",
        "parameters": {
            "type": "object",
            "properties": {
                "portfolio": {
                    "type": "string",
                    "description": "JSON string of portfolio weights, e.g. '{\"SPY\":0.6,\"AGG\":0.4}'",
                },
                "metric": {
                    "type": "string",
                    "enum": ["var", "sharpe", "beta"],
                    "description": "Risk metric to calculate",
                },
            },
            "required": ["portfolio", "metric"],
        },
    },
}

SCREEN_FUNDS_TOOL = {
    "type": "function",
    "function": {
        "name": "screen_funds",
        "description": "Screen PE or hedge funds based on criteria.",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string", "description": "Fund strategy filter"},
                "min_aum": {"type": "number", "description": "Minimum AUM in millions"},
                "vintage_year": {"type": "integer", "description": "Fund vintage year"},
            },
        },
    },
}

SEC_FILING_TOOL = {
    "type": "function",
    "function": {
        "name": "get_sec_filing",
        "description": "Retrieve a specific SEC filing for a company.",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name or ticker"},
                "filing_type": {
                    "type": "string",
                    "enum": ["10-K", "10-Q", "8-K", "S-1", "13F"],
                    "description": "SEC filing type",
                },
            },
            "required": ["company", "filing_type"],
        },
    },
}

CALCULATE_RETURNS_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_returns",
        "description": "Calculate financial returns or perform financial math.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Financial calculation expression or description",
                },
            },
            "required": ["expression"],
        },
    },
}


class ToolUseBenchmark(BaseBenchmark):
    name = "Tool Use"
    category = "Tool Use"
    description = "Function calling: stock quotes, risk metrics, SEC filings, fund screening."

    def get_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id="tool_01",
                prompt="What is the current stock price of Apple?",
                tools=[STOCK_QUOTE_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": "get_stock_quote",
                    "expected_args": {"symbol": "AAPL"},
                },
            ),
            BenchmarkTask(
                task_id="tool_02",
                prompt="Get me the latest 10-K filing for Tesla.",
                tools=[SEC_FILING_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": "get_sec_filing",
                    "expected_args": {"filing_type": "10-K"},
                    "expected_args_pattern": {"company": r"(?i)tesla|TSLA"},
                },
            ),
            BenchmarkTask(
                task_id="tool_03",
                prompt=(
                    "Calculate the annualized return on a $100,000 investment that "
                    "grew to $150,000 over 3 years."
                ),
                tools=[CALCULATE_RETURNS_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": "calculate_returns",
                    "expected_args_contains": ["100000", "150000"],
                },
            ),
            BenchmarkTask(
                task_id="tool_04",
                prompt=(
                    "Screen for private equity funds with AUM over $500 million "
                    "and vintage year 2020."
                ),
                tools=[SCREEN_FUNDS_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": "screen_funds",
                    "expected_args_pattern": {
                        "min_aum": r"500",
                    },
                },
            ),
            BenchmarkTask(
                task_id="tool_05",
                prompt=(
                    "Calculate the Value at Risk for my portfolio consisting of "
                    "60% SPY and 40% AGG."
                ),
                tools=[PORTFOLIO_RISK_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": "calculate_portfolio_risk",
                    "expected_args_pattern": {"metric": r"(?i)var"},
                },
            ),
            BenchmarkTask(
                task_id="tool_06",
                prompt=(
                    "I need Apple's stock price and also Tesla's latest 8-K filing."
                ),
                tools=[STOCK_QUOTE_TOOL, SEC_FILING_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tools": ["get_stock_quote", "get_sec_filing"],
                    "multi_tool": True,
                },
            ),
            BenchmarkTask(
                task_id="tool_07",
                prompt="What is the definition of a hedge fund? Don't use any tools.",
                tools=[STOCK_QUOTE_TOOL, CALCULATE_RETURNS_TOOL, SCREEN_FUNDS_TOOL],
                eval_method=EvalMethod.TOOL_TRAJECTORY,
                eval_criteria={
                    "expected_tool": None,
                    "should_not_call_tools": True,
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        import re

        tool_calls: list[dict] = kwargs.get("tool_calls", [])
        criteria = task.eval_criteria

        if criteria.get("should_not_call_tools"):
            return 100.0 if not tool_calls else 0.0

        if not tool_calls:
            return 0.0

        score = 0.0
        total_checks = 0

        if criteria.get("multi_tool"):
            expected_tools = set(criteria.get("expected_tools", []))
            called_tools = set()
            for tc in tool_calls:
                fn = tc.get("function", {})
                called_tools.add(fn.get("name", ""))
            total_checks = len(expected_tools)
            score = len(expected_tools & called_tools) / max(total_checks, 1) * 100
            return round(score, 1)

        tc = tool_calls[0]
        fn = tc.get("function", {})
        called_name = fn.get("name", "")
        try:
            called_args = json.loads(fn.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            called_args = {}

        expected_tool = criteria.get("expected_tool")
        total_checks += 1
        if called_name == expected_tool:
            score += 1

        expected_args = criteria.get("expected_args", {})
        for key, val in expected_args.items():
            total_checks += 1
            if str(called_args.get(key, "")).lower() == str(val).lower():
                score += 1

        expected_contains = criteria.get("expected_args_contains", [])
        for val in expected_contains:
            total_checks += 1
            args_str = json.dumps(called_args)
            if val in args_str:
                score += 1

        expected_patterns = criteria.get("expected_args_pattern", {})
        for key, pattern in expected_patterns.items():
            total_checks += 1
            arg_val = str(called_args.get(key, ""))
            if re.search(pattern, arg_val):
                score += 1

        return round((score / max(total_checks, 1)) * 100, 1)
