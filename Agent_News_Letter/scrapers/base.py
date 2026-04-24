from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    summary: str
    published_date: datetime
    authors: list[str] = field(default_factory=list)
    score: float = 0.0
    category: str = ""
    ai_summary: str = ""

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NewsItem):
            return NotImplemented
        return self.url == other.url


class BaseScraper(ABC):
    """Common interface every source scraper must implement."""

    name: str = "base"

    @abstractmethod
    async def fetch(self) -> list[NewsItem]:
        """Return news items discovered in the last ~24 hours."""

    async def safe_fetch(self) -> list[NewsItem]:
        """Wrapper that catches exceptions so one failing scraper
        doesn't take down the whole pipeline."""
        try:
            items = await self.fetch()
            logger.info("%s returned %d items", self.name, len(items))
            return items
        except Exception:
            logger.exception("Scraper %s failed", self.name)
            return []
