from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser

from config.settings import GOOGLE_NEWS_QUERIES
from scrapers.base import BaseScraper, NewsItem

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class WebScraper(BaseScraper):
    """Scrapes Google News RSS for broad AI coverage."""

    name = "google_news"

    async def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []

        for query in GOOGLE_NEWS_QUERIES:
            url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
            try:
                feed = await asyncio.to_thread(feedparser.parse, url)
            except Exception:
                logger.warning("Google News RSS failed for query: %s", query)
                continue

            for entry in feed.entries[:10]:
                pub_date = datetime.now(timezone.utc)
                raw_date = entry.get("published")
                if raw_date:
                    try:
                        pub_date = parsedate_to_datetime(raw_date).astimezone(
                            timezone.utc
                        )
                    except Exception:
                        pass

                source_name = entry.get("source", {})
                if isinstance(source_name, dict):
                    source_name = source_name.get("title", "Google News")
                else:
                    source_name = "Google News"

                items.append(
                    NewsItem(
                        title=entry.get("title", "Untitled"),
                        url=entry.get("link", ""),
                        source=self.name,
                        summary=entry.get("summary", "")[:500],
                        published_date=pub_date,
                        authors=[source_name],
                    )
                )

        return items
