from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import arxiv

from config.settings import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS
from scrapers.base import BaseScraper, NewsItem

logger = logging.getLogger(__name__)


class ArxivScraper(BaseScraper):
    name = "arxiv"

    async def fetch(self) -> list[NewsItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        query = " OR ".join(f"cat:{cat}" for cat in ARXIV_CATEGORIES)

        search = arxiv.Search(
            query=query,
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        items: list[NewsItem] = []
        results = await asyncio.to_thread(list, arxiv.Client().results(search))

        for result in results:
            published = result.published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue
            items.append(
                NewsItem(
                    title=result.title.replace("\n", " ").strip(),
                    url=result.entry_id,
                    source=self.name,
                    summary=result.summary.replace("\n", " ").strip()[:500],
                    published_date=published,
                    authors=[a.name for a in result.authors[:5]],
                )
            )

        return items
