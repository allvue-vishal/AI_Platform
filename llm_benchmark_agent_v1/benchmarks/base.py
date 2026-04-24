"""Base classes and data models for benchmarks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class EvalMethod(str, Enum):
    EXACT_MATCH = "exact_match"
    NUMERIC_MATCH = "numeric_match"
    REGEX_MATCH = "regex_match"
    JSON_VALIDATION = "json_validation"
    CODE_EXECUTION = "code_execution"
    LLM_JUDGE = "llm_judge"
    TOOL_TRAJECTORY = "tool_trajectory"
    RULE_BASED = "rule_based"


@dataclass
class BenchmarkTask:
    task_id: str
    prompt: str  # user message
    system_prompt: str = ""
    expected_answer: str = ""
    eval_method: EvalMethod = EvalMethod.EXACT_MATCH
    eval_criteria: dict = field(default_factory=dict)
    tools: list[dict] | None = None
    conversation_turns: list[list[dict]] | None = None  # for multi-turn tasks
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskResult:
    task_id: str
    model: str
    score: float  # 0-100
    response: str
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    benchmark_name: str
    category: str
    model: str
    avg_score: float
    avg_latency: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost: float
    task_results: list[TaskResult] = field(default_factory=list)


class BaseBenchmark(ABC):
    name: str = ""
    category: str = ""
    description: str = ""

    @abstractmethod
    def get_tasks(self) -> list[BenchmarkTask]:
        """Return all test tasks for this benchmark."""

    @abstractmethod
    def evaluate(self, task: BenchmarkTask, response: str, **kwargs) -> float:
        """Score a single response. Returns 0-100."""
