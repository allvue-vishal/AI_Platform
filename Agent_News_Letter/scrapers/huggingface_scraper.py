from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, NewsItem

logger = logging.getLogger(__name__)

HF_PAPERS_URL = "https://huggingface.co/papers"


class HuggingFaceScraper(BaseScraper):
    name = "huggingface"

    async def fetch(self) -> list[NewsItem]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                HF_PAPERS_URL,
                headers={"User-Agent": "AgentJarvis/1.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        items: list[NewsItem] = []

        for article in soup.select("article"):
            link_tag = article.select_one("a[href*='/papers/']")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            url = f"https://huggingface.co{href}" if href.startswith("/") else href

            summary_tag = article.select_one("p")
            summary = summary_tag.get_text(strip=True)[:500] if summary_tag else ""

            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source=self.name,
                    summary=summary,
                    published_date=datetime.now(timezone.utc),
                    authors=[],
                )
            )

        return items
