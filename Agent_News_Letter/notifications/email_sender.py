from __future__ import annotations

import base64
import logging
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from agent.schemas import DigestReport
from config.settings import BASE_DIR, RECIPIENT_EMAIL, TEMPLATE_DIR

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"


def _render_email(report: DigestReport) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("email_template.html")

    categories: dict[str, list] = defaultdict(list)
    for item in report.items:
        if item != report.top_story:
            categories[item.category].append(item)

    return template.render(
        date=report.date,
        top_story=report.top_story,
        categories=dict(categories),
    )


def _get_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not CREDENTIALS_PATH.exists():
        logger.error(
            "credentials.json not found at %s — see README for setup instructions",
            CREDENTIALS_PATH,
        )
        return None

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_digest(report: DigestReport) -> bool:
    """Render the digest report as HTML and send via Gmail API."""
    if not RECIPIENT_EMAIL:
        logger.error("RECIPIENT_EMAIL not configured — check .env")
        return False

    html_body = _render_email(report)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Atlas - Daily Digest ({report.date})"
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        service = _get_gmail_service()
        if service is None:
            return False

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(
            userId="me", body={"raw": raw_message}
        ).execute()

        logger.info("Digest email sent to %s via Gmail API", RECIPIENT_EMAIL)
        return True

    except Exception:
        logger.exception("Gmail API send failed")
        return False
