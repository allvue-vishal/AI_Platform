"""LangChain tools that wrap the data-source scrapers.

Each tool runs the underlying scraper synchronously (via asyncio) and returns
a formatted text block the agent can reason over.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import arxiv
import feedparser
from langchain_core.tools import tool

from config.settings import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS, GOOGLE_NEWS_QUERIES

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()


@tool
def search_arxiv(categories: str = "cs.AI,cs.LG,cs.CL,cs.CV") -> str:
    """Search ArXiv for the latest AI research papers published in the last 48 hours.

    Args:
        categories: Comma-separated ArXiv categories to search (default: cs.AI,cs.LG,cs.CL,cs.CV)

    Returns:
        Formatted list of recent papers with titles, URLs, and abstracts.
    """
    cats = [c.strip() for c in categories.split(",")]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    query = " OR ".join(f"cat:{cat}" for cat in cats)

    search = arxiv.Search(
        query=query,
        max_results=ARXIV_MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = list(arxiv.Client().results(search))
    lines: list[str] = []

    for r in results:
        published = r.published.replace(tzinfo=timezone.utc)
        if published < cutoff:
            continue
        title = r.title.replace("\n", " ").strip()
        abstract = r.summary.replace("\n", " ").strip()[:300]
        lines.append(f"- {title}\n  URL: {r.entry_id}\n  Abstract: {abstract}\n")

    if not lines:
        return "No new ArXiv papers found in the last 48 hours for the given categories."

    return f"Found {len(lines)} recent ArXiv papers:\n\n" + "\n".join(lines)


@tool
def search_huggingface() -> str:
    """Get today's trending AI research papers from HuggingFace Daily Papers.

    Returns:
        Formatted list of trending papers with titles, URLs, and descriptions.
    """
    import aiohttp
    from bs4 import BeautifulSoup

    async def _fetch():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://huggingface.co/papers",
                headers={"User-Agent": "AIAtlas/1.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                return await resp.text()

    try:
        html = _run_async(_fetch())
    except Exception as e:
        return f"HuggingFace scraping failed: {e}"

    soup = BeautifulSoup(html, "html.parser")
    lines: list[str] = []

    for article in soup.select("article"):
        link_tag = article.select_one("a[href*='/papers/']")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        url = f"https://huggingface.co{href}" if href.startswith("/") else href
        summary_tag = article.select_one("p")
        summary = summary_tag.get_text(strip=True)[:300] if summary_tag else ""
        lines.append(f"- {title}\n  URL: {url}\n  Summary: {summary}\n")

    if not lines:
        return "No trending papers found on HuggingFace today."

    return f"Found {len(lines)} trending HuggingFace papers:\n\n" + "\n".join(lines)


@tool
def search_google_news(query: str = "artificial intelligence breakthrough") -> str:
    """Search Google News for the latest AI news and advancements.

    Args:
        query: Search query for Google News (e.g., "AI breakthrough", "large language model research")

    Returns:
        Formatted list of recent news articles with titles and URLs.
    """
    rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        return f"Google News search failed: {e}"

    lines: list[str] = []
    for entry in feed.entries[:15]:
        title = entry.get("title", "Untitled")
        url = entry.get("link", "")
        source = entry.get("source", {})
        pub = source.get("title", "Unknown") if isinstance(source, dict) else "Unknown"
        lines.append(f"- {title} (via {pub})\n  URL: {url}\n")

    if not lines:
        return f"No Google News results found for query: {query}"

    return f"Found {len(lines)} news articles for '{query}':\n\n" + "\n".join(lines)


ALL_TOOLS = [search_arxiv, search_huggingface, search_google_news]
