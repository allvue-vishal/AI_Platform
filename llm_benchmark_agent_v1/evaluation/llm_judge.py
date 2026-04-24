"""LLM-as-judge evaluator for subjective tasks."""

from __future__ import annotations

import json
import re

from models.runner import run_prompt
from config import settings


JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator. You will be given a task prompt and a model's response.
Rate the response on a scale of 1-10 based on the provided rubric.

You MUST respond with ONLY a valid JSON object in this exact format:
{"score": <number 1-10>, "reasoning": "<brief explanation>"}

Do not include any other text before or after the JSON."""

JUDGE_USER_TEMPLATE = """\
## Task Prompt
{task_prompt}

## Rubric
{rubric}

## Model Response
{response}

Rate the response 1-10 based on the rubric. Respond with only JSON: {{"score": <1-10>, "reasoning": "<brief>"}}"""


def judge_response(
    task_prompt: str,
    response: str,
    rubric: str,
    judge_model: str | None = None,
) -> tuple[float, str]:
    """Use an LLM to judge a response. Returns (score 0-100, reasoning)."""
    model = judge_model or settings.JUDGE_MODEL
    if not model:
        return 50.0, "No judge model configured; returning default score."

    user_msg = JUDGE_USER_TEMPLATE.format(
        task_prompt=task_prompt,
        rubric=rubric,
        response=response,
    )

    result = run_prompt(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        max_tokens=512,
    )

    if result.error:
        return 50.0, f"Judge error: {result.error}"

    return _parse_judge_response(result.content)


def judge_conversation(
    turns_summary: str,
    rubric: str,
    judge_model: str | None = None,
) -> tuple[float, str]:
    """Judge a multi-turn conversation."""
    model = judge_model or settings.JUDGE_MODEL
    if not model:
        return 50.0, "No judge model configured."

    user_msg = (
        f"## Multi-turn Conversation\n{turns_summary}\n\n"
        f"## Rubric\n{rubric}\n\n"
        f"Rate the assistant's overall performance 1-10. "
        f'Respond with only JSON: {{"score": <1-10>, "reasoning": "<brief>"}}'
    )

    result = run_prompt(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        max_tokens=512,
    )

    if result.error:
        return 50.0, f"Judge error: {result.error}"

    return _parse_judge_response(result.content)


def _parse_judge_response(text: str) -> tuple[float, str]:
    """Extract score and reasoning from judge output."""
    try:
        cleaned = text.strip()
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            score = float(data.get("score", 5))
            score = max(1.0, min(10.0, score))
            reasoning = data.get("reasoning", "")
            return round(score * 10, 1), reasoning
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
    for n in numbers:
        val = float(n)
        if 1 <= val <= 10:
            return round(val * 10, 1), text[:200]

    return 50.0, f"Could not parse judge response: {text[:200]}"
