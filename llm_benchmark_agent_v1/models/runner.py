"""Send prompts to models via LiteLLM proxy using the OpenAI SDK."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from openai import OpenAI
from config import settings


@dataclass
class RunResult:
    model: str
    content: str
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error: str | None = None
    tool_calls: list[dict] = field(default_factory=list)


def _build_client() -> OpenAI:
    return OpenAI(
        api_key=settings.LITELLM_API_KEY or "no-key",
        base_url=f"{settings.LITELLM_PROXY_URL.rstrip('/')}/v1",
        timeout=settings.REQUEST_TIMEOUT,
    )


def run_prompt(
    model: str,
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: int = 2048,
    tools: list[dict] | None = None,
) -> RunResult:
    """Send a chat completion request and capture response + metrics."""
    client = _build_client()
    start = time.perf_counter()
    try:
        kwargs: dict = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)
        elapsed = time.perf_counter() - start

        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls_raw = choice.message.tool_calls or []
        tool_calls = []
        for tc in tool_calls_raw:
            tool_calls.append(
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )

        usage = response.usage
        return RunResult(
            model=model,
            content=content,
            latency_seconds=round(elapsed, 3),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            tool_calls=tool_calls,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return RunResult(
            model=model,
            content="",
            latency_seconds=round(elapsed, 3),
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error=str(exc),
        )


def run_multi_turn(
    model: str,
    conversation_turns: list[list[dict]],
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> list[RunResult]:
    """Run a multi-turn conversation, feeding each assistant reply back."""
    client = _build_client()
    messages: list[dict] = []
    results: list[RunResult] = []

    for turn_messages in conversation_turns:
        messages.extend(turn_messages)
        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = time.perf_counter() - start
            choice = response.choices[0]
            content = choice.message.content or ""
            messages.append({"role": "assistant", "content": content})
            usage = response.usage
            results.append(
                RunResult(
                    model=model,
                    content=content,
                    latency_seconds=round(elapsed, 3),
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                )
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            results.append(
                RunResult(
                    model=model,
                    content="",
                    latency_seconds=round(elapsed, 3),
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    error=str(exc),
                )
            )
            break

    return results
