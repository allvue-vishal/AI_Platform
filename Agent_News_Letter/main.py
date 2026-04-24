"""AI Atlas -- Daily AI Research Digest powered by LangChain.

A ReAct agent that autonomously searches ArXiv, HuggingFace, and Google News
for the latest AI advancements, then produces a structured digest.

Usage:
    python main.py          # run agent and send email
    python main.py --dry    # run agent and print digest to console (no email)
"""

from __future__ import annotations

import truststore
truststore.inject_into_ssl()

import io
import logging
import sys
from datetime import datetime, timezone

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from config.settings import LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ai_atlas")


def main() -> None:
    dry_run = "--dry" in sys.argv
    start = datetime.now(timezone.utc)
    logger.info("=== AI Atlas started ===")

    from agent.atlas import run_agent

    try:
        report = run_agent()
    except Exception:
        logger.exception("Agent failed to produce a digest")
        return

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Agent completed in %.1fs -- %d items in digest", elapsed, len(report.items))

    if dry_run:
        print(f"\n{'='*60}")
        print(f"  AI ATLAS - Daily AI Digest ({report.date})")
        print(f"{'='*60}")
        print(f"\n  TOP STORY [{report.top_story.category}]")
        print(f"  {report.top_story.title}")
        print(f"  {report.top_story.summary}")
        print(f"  {report.top_story.url}")
        print(f"\n{'-'*60}")
        for item in report.items:
            if item == report.top_story:
                continue
            print(f"\n  [{item.category}] ({item.significance}/10)")
            print(f"  {item.title}")
            print(f"  {item.summary}")
            print(f"  {item.url}")
        print(f"\n{'='*60}\n")
    else:
        from notifications.email_sender import send_digest
        if send_digest(report):
            logger.info("Digest email sent successfully!")
        else:
            logger.error("Failed to send digest email")

    logger.info("=== AI Atlas finished ===")


if __name__ == "__main__":
    main()
