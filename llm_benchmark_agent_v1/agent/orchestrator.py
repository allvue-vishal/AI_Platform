"""LangChain agent orchestrator for LLM benchmarking."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import settings
from agent.tools import (
    discover_models,
    list_benchmark_categories,
    run_benchmark,
    run_all_benchmarks,
    generate_report,
    get_best_model_for,
)


SYSTEM_PROMPT = """\
You are an LLM Benchmarking Agent. Your job is to help users evaluate and compare \
language models available on their LiteLLM proxy.

You have tools to:
1. Discover available models on the proxy
2. List all benchmark categories (Code Generation, Math, Reasoning, etc.)
3. Run benchmarks on specific models and categories
4. Run all benchmarks across multiple models
5. Generate reports (CLI, HTML, CSV)
6. Recommend the best model for a given use case

When the user asks you to benchmark models, follow this approach:
- First discover which models are available
- Run the requested benchmarks
- Present results clearly and generate reports

When asked which model is best for a use case, consult the benchmark results.
If no results exist yet, suggest running the relevant benchmarks first.

Be concise and data-driven in your responses. Always cite specific scores."""


def build_agent(agent_model: str | None = None) -> AgentExecutor:
    """Create and return the benchmarking agent."""
    model_name = agent_model or settings.JUDGE_MODEL or "gpt-4o"

    llm = ChatOpenAI(
        model=model_name,
        api_key=settings.LITELLM_API_KEY or "no-key",
        base_url=f"{settings.LITELLM_PROXY_URL.rstrip('/')}/v1",
        temperature=0,
    )

    tools = [
        discover_models,
        list_benchmark_categories,
        run_benchmark,
        run_all_benchmarks,
        generate_report,
        get_best_model_for,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=20,
    )


def run_agent_interactive():
    """Start an interactive agent session."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel(
        "[bold]LLM Benchmark Agent[/bold]\n"
        "Ask me to benchmark models, compare them, or recommend the best model for your use case.\n"
        "Type 'quit' or 'exit' to stop.",
        title="Welcome",
        border_style="blue",
    ))

    agent = build_agent()
    chat_history: list = []

    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        try:
            result = agent.invoke({
                "input": user_input,
                "chat_history": chat_history,
            })
            output = result.get("output", "No response.")
            console.print(f"\n[bold green]Agent:[/bold green] {output}")

            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": output})
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
