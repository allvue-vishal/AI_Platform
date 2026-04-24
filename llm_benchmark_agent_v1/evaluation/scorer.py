"""Unified scoring engine that dispatches to deterministic or LLM-based evaluation."""

from __future__ import annotations

from benchmarks.base import BaseBenchmark, BenchmarkTask, BenchmarkResult, TaskResult, EvalMethod
from models.runner import RunResult, run_prompt, run_multi_turn
from evaluation.llm_judge import judge_response, judge_conversation
from rich.console import Console

console = Console()


def run_and_score_task(
    benchmark: BaseBenchmark,
    task: BenchmarkTask,
    model: str,
    judge_model: str | None = None,
) -> TaskResult:
    """Run a single task against a model and score it."""

    if task.conversation_turns:
        return _run_conversation_task(benchmark, task, model, judge_model)

    messages = []
    if task.system_prompt:
        messages.append({"role": "system", "content": task.system_prompt})
    messages.append({"role": "user", "content": task.prompt})

    result = run_prompt(
        model=model,
        messages=messages,
        tools=task.tools,
    )

    if result.error:
        return TaskResult(
            task_id=task.task_id,
            model=model,
            score=0.0,
            response="",
            latency_seconds=result.latency_seconds,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            error=result.error,
        )

    score = _compute_score(benchmark, task, result, judge_model)

    return TaskResult(
        task_id=task.task_id,
        model=model,
        score=score,
        response=result.content,
        latency_seconds=result.latency_seconds,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
    )


def _compute_score(
    benchmark: BaseBenchmark,
    task: BenchmarkTask,
    result: RunResult,
    judge_model: str | None,
) -> float:
    """Dispatch scoring based on eval method."""
    if task.eval_method == EvalMethod.LLM_JUDGE:
        rubric = task.eval_criteria.get("rubric", "Rate quality 1-10.")
        score, _ = judge_response(
            task_prompt=task.prompt,
            response=result.content,
            rubric=rubric,
            judge_model=judge_model,
        )
        return score

    if task.eval_method == EvalMethod.TOOL_TRAJECTORY:
        return benchmark.evaluate(
            task, result.content, tool_calls=result.tool_calls
        )

    return benchmark.evaluate(task, result.content)


def _run_conversation_task(
    benchmark: BaseBenchmark,
    task: BenchmarkTask,
    model: str,
    judge_model: str | None,
) -> TaskResult:
    """Handle multi-turn conversation tasks."""
    turns = task.conversation_turns or []
    results = run_multi_turn(model=model, conversation_turns=turns)

    if not results:
        return TaskResult(
            task_id=task.task_id,
            model=model,
            score=0.0,
            response="",
            latency_seconds=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error="No responses from multi-turn conversation",
        )

    total_latency = sum(r.latency_seconds for r in results)
    total_prompt = sum(r.prompt_tokens for r in results)
    total_completion = sum(r.completion_tokens for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    conversation_log = []
    for i, (turn_msgs, res) in enumerate(zip(turns, results)):
        for msg in turn_msgs:
            conversation_log.append(f"User: {msg['content']}")
        conversation_log.append(f"Assistant: {res.content}")
    summary = "\n\n".join(conversation_log)

    rubric = task.eval_criteria.get("rubric", "Rate the conversation quality 1-10.")
    score, _ = judge_conversation(
        turns_summary=summary,
        rubric=rubric,
        judge_model=judge_model,
    )

    full_response = "\n---\n".join(r.content for r in results)
    error = results[-1].error if results[-1].error else None

    return TaskResult(
        task_id=task.task_id,
        model=model,
        score=score,
        response=full_response,
        latency_seconds=total_latency,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        total_tokens=total_tokens,
        error=error,
    )


def run_benchmark_for_model(
    benchmark: BaseBenchmark,
    model: str,
    judge_model: str | None = None,
) -> BenchmarkResult:
    """Run all tasks in a benchmark for a specific model."""
    tasks = benchmark.get_tasks()
    task_results: list[TaskResult] = []

    for task in tasks:
        console.print(f"  [dim]Running {task.task_id}...[/dim]", end=" ")
        tr = run_and_score_task(benchmark, task, model, judge_model)
        status = f"[green]{tr.score:.0f}[/green]" if tr.score >= 70 else (
            f"[yellow]{tr.score:.0f}[/yellow]" if tr.score >= 40 else f"[red]{tr.score:.0f}[/red]"
        )
        console.print(status)
        task_results.append(tr)

    avg_score = sum(t.score for t in task_results) / len(task_results) if task_results else 0.0
    avg_latency = sum(t.latency_seconds for t in task_results) / len(task_results) if task_results else 0.0
    total_prompt = sum(t.prompt_tokens for t in task_results)
    total_completion = sum(t.completion_tokens for t in task_results)
    total_tokens = sum(t.total_tokens for t in task_results)

    cost = _estimate_cost(model, total_prompt, total_completion)

    return BenchmarkResult(
        benchmark_name=benchmark.name,
        category=benchmark.category,
        model=model,
        avg_score=round(avg_score, 1),
        avg_latency=round(avg_latency, 3),
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        total_tokens=total_tokens,
        estimated_cost=round(cost, 6),
        task_results=task_results,
    )


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Rough cost estimate; falls back to LiteLLM's cost map when available."""
    try:
        import litellm
        prompt_cost = litellm.completion_cost(
            model=model,
            prompt="x",
            completion="x",
        )
        if prompt_cost:
            return prompt_cost
    except Exception:
        pass

    default_input_rate = 0.000003   # $3 per 1M tokens
    default_output_rate = 0.000015  # $15 per 1M tokens
    return (prompt_tokens * default_input_rate) + (completion_tokens * default_output_rate)
