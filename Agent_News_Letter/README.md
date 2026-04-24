# AI Atlas

A **LangGraph ReAct agent** that autonomously gathers the latest AI research and news, reasons over the results, and produces a structured daily digest delivered to your inbox via the **Gmail API**.

## Features

- **Three search tools** — ArXiv papers, HuggingFace trending papers, and Google News RSS
- **Intelligent filtering** — the agent deduplicates, categorizes, and ranks items by significance
- **Structured output** — Pydantic `DigestReport` with a top story and scored items
- **HTML email** — beautifully formatted digest sent through Gmail OAuth
- **Scheduled runs** — optional Windows Task Scheduler setup for daily execution

## Data Sources

| Source | What it pulls |
|--------|---------------|
| **ArXiv** | Recent papers in configurable categories (default: cs.AI, cs.LG, cs.CL, cs.CV), last 48 hours |
| **HuggingFace** | Trending community-curated papers from [huggingface.co/papers](https://huggingface.co/papers) |
| **Google News** | Industry news and announcements via Google News RSS |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/Agent_News_Letter.git
cd Agent_News_Letter
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Edit `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `LITELLM_API_KEY` | Yes | API key for your LLM provider (any backend LiteLLM supports) |
| `LITELLM_API_BASE` | No | Custom base URL (e.g. LiteLLM proxy) |
| `LITELLM_MODEL` | Yes | Model identifier, e.g. `anthropic/claude-sonnet-4-20250514` or `openai/gpt-4o` |
| `RECIPIENT_EMAIL` | Yes | Email address to receive the daily digest |

### 3. Set up Gmail API (for sending email)

Email delivery uses **OAuth 2.0**, not SMTP app passwords.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Gmail API**.
3. Configure the **OAuth consent screen** (External is fine for personal use).
4. Create an **OAuth 2.0 Client ID** with application type **Desktop app**.
5. Download the client secret JSON and save it as **`credentials.json`** in the project root.

The first time you run without `--dry`, a browser window will open to authorize the app. Tokens are cached in `token.json` (git-ignored).

### 4. Run

**Dry run** — builds the digest and prints it to the console (no email sent):

```bash
python main.py --dry
```

**Full run** — builds the digest and sends it via email:

```bash
python main.py
```

Logs are written to `logs/ai_atlas.log`.

### 5. Schedule daily (Windows)

Run `setup_scheduler.bat` as Administrator to register a task that runs `main.py` every day at 07:00.

```bash
setup_scheduler.bat
```

To change the time, edit `RUN_TIME` in the batch file before running it. To remove the scheduled task:

```bash
schtasks /delete /tn "AIAtlas_DailyDigest" /f
```

## Project Structure

```
Agent_News_Letter/
├── main.py                    # Entry point (--dry flag, logging, orchestration)
├── agent/
│   ├── atlas.py               # LangGraph ReAct agent (ChatLiteLLM + structured output)
│   ├── tools.py               # search_arxiv, search_huggingface, search_google_news
│   └── schemas.py             # DigestItem, DigestReport (Pydantic models)
├── config/
│   └── settings.py            # Environment loading, ArXiv categories, news queries, paths
├── notifications/
│   └── email_sender.py        # Jinja2 HTML rendering + Gmail API send
├── templates/
│   └── email_template.html    # Email HTML template
├── scrapers/                  # Legacy async scrapers (not wired to the agent)
├── setup_scheduler.bat        # Windows Task Scheduler helper
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── .gitignore
```

## How It Works

1. **Agent** — `create_react_agent` (LangGraph) with a system prompt that enforces tool use, filtering, and categorization into **LLMs**, **Computer Vision**, **Robotics**, **AI Safety**, **Tools & Frameworks**, and **Industry**.
2. **Structured output** — the agent's final response is parsed into a `DigestReport` (date, top story, ranked items).
3. **Email** — `email_template.html` is rendered with Jinja2 and sent through the Gmail API.

## Customization

| What | Where |
|------|-------|
| ArXiv categories & depth | `ARXIV_MAX_RESULTS`, `ARXIV_CATEGORIES` in `config/settings.py` |
| Google News seed queries | `GOOGLE_NEWS_QUERIES` in `config/settings.py` |
| Digest categories / report shape | `agent/schemas.py` and system prompt in `agent/atlas.py` |
| Email layout | `templates/email_template.html` |

## License

This project is provided as-is for personal use.
