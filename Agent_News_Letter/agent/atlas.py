"""AI Atlas -- LangChain ReAct agent for daily AI research digests."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from langchain_litellm import ChatLiteLLM
from langgraph.prebuilt import create_react_agent

from agent.schemas import DigestReport
from agent.tools import ALL_TOOLS
from config.settings import LITELLM_API_BASE, LITELLM_API_KEY, LITELLM_MODEL

logger = logging.getLogger(__name__)


def _system_prompt() -> str:
    """Build the system prompt with the current date (evaluated at call time)."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return f"""\
You are **AI Atlas**, an expert AI research analyst. Today is {today}.

Your mission: produce a comprehensive daily digest of the most important AI advancements, \
research papers, and breakthroughs from the last 24-48 hours.

## Instructions

1. **Use ALL three tools** to gather broad coverage:
   - `search_arxiv` -- for cutting-edge research papers
   - `search_huggingface` -- for trending community-curated papers
   - `search_google_news` -- for industry news and announcements (try 2-3 different queries \
like "AI breakthrough", "large language model research", "artificial intelligence advancement")

2. **Filter ruthlessly** -- include ONLY:
   - New research papers and their findings
   - Model releases and technical announcements
   - Genuine scientific breakthroughs and advancements
   - Important open-source tool/framework releases

3. **Exclude** all of the following:
   - Opinion pieces, editorials, speculation
   - Job postings, career advice, conference logistics
   - Memes, humor, general discussion threads
   - Product marketing that isn't a genuine technical advancement
   - Duplicate items (same paper appearing on ArXiv and HuggingFace -- keep one)

4. **For each item** write a clear 2-3 sentence summary explaining:
   - What was done (the method/approach)
   - Why it matters (the significance)
   - Keep it accessible to a technical audience

5. **Categorize** each item into exactly one of: LLMs, Computer Vision, Robotics, \
AI Safety, Tools & Frameworks, Industry

6. **Rank** by genuine significance (1-10, where 10 = field-changing breakthrough)

7. **Pick the single most important item** as the top story.

8. **Use "{today}" as the date** in the DigestReport.

9. Return your final answer as a structured DigestReport.
"""


def build_agent():
    """Create and return the AI Atlas LangChain agent."""
    llm = ChatLiteLLM(
        model=LITELLM_MODEL,
        api_key=LITELLM_API_KEY,
        api_base=LITELLM_API_BASE or None,
        temperature=0.2,
        max_tokens=8192,
    )

    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=_system_prompt(),
        response_format=DigestReport,
    )

    return agent


def run_agent() -> DigestReport:
    """Invoke the agent and return a structured DigestReport."""
    agent = build_agent()
    logger.info("AI Atlas agent created, invoking...")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Generate today's AI daily digest."}]}
    )

    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("Agent did not produce a structured DigestReport")

    logger.info(
        "Agent produced digest with %d items (top story: %s)",
        len(structured.items),
        structured.top_story.title[:60],
    )
    return structured
