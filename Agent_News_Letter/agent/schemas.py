from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Category = Literal[
    "LLMs",
    "Computer Vision",
    "Robotics",
    "AI Safety",
    "Tools & Frameworks",
    "Industry",
]


class DigestItem(BaseModel):
    """A single AI news/research item in the daily digest."""

    title: str = Field(description="Title of the paper, article, or announcement")
    url: str = Field(description="Direct link to the source")
    category: Category = Field(description="AI sub-field this item belongs to")
    significance: int = Field(ge=1, le=10, description="Importance score, 10 = groundbreaking")
    summary: str = Field(description="2-3 sentence plain-English summary of the advancement")


class DigestReport(BaseModel):
    """Structured daily AI digest produced by the agent."""

    date: str = Field(description="Today's date in 'Month DD, YYYY' format")
    top_story: DigestItem = Field(description="The single most significant development today")
    items: list[DigestItem] = Field(description="All items sorted by significance descending")
