# LLM Benchmark Agent

A LangChain-based agent that auto-discovers models on a LiteLLM proxy, benchmarks them across 10 domain-specific categories, and produces ranked reports. Includes a Streamlit dashboard and public leaderboard comparison.

## Features

- **Auto-Discovery** — Automatically detects all models available on your LiteLLM proxy
- **10 Benchmark Categories** — Covers reasoning, math, coding, summarization, classification, knowledge, tool use, conversation, financial analysis, and regulatory compliance
- **Multiple Evaluation Methods** — Exact match, regex, numeric tolerance, code execution, tool trajectory, and LLM-as-judge
- **Rich Reporting** — CLI tables (Rich), interactive HTML (Jinja2 + Plotly), and CSV export
- **Streamlit Dashboard** — Interactive web UI with leaderboard, per-category drill-down, and public benchmark comparison
- **Public Leaderboard Comparison** — Side-by-side view with HuggingFace Open LLM Leaderboard scores

## Prerequisites

- Python 3.10+
- Access to a [LiteLLM Proxy](https://docs.litellm.ai/) with one or more deployed models

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd llm_benchmark_agent_V1
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual configuration:

```env
LITELLM_PROXY_URL=http://localhost:4000    # Your LiteLLM proxy URL
LITELLM_API_KEY=your-api-key-here          # Your LiteLLM API key
JUDGE_MODEL=gpt-4o                         # Model used for LLM-as-judge evaluation
REQUEST_TIMEOUT=120                        # Request timeout in seconds
AGENT_MODEL=                               # (Optional) Model for interactive agent mode
RESULTS_DIR=data/results                   # Directory to store benchmark results
```

## Benchmark Categories

| Category       | Description                                              | Evaluation Method           |
|----------------|----------------------------------------------------------|-----------------------------|
| Reasoning      | Syllogisms, incentive logic, return math traps           | Exact/regex/numeric match   |
| Math           | NPV, IRR, WACC, bond pricing, mortgage calculations     | Numeric match               |
| Coding         | Python code: returns, Sharpe ratio, amortization, CAGR   | Code execution              |
| Summarization  | Earnings calls, 10-K filings, FOMC statements            | LLM-as-judge                |
| Classification | Sentiment, document type, news category, fraud detection | Exact match                 |
| Knowledge      | Fund structures, regulations, valuation concepts         | Exact/numeric/regex match   |
| Tool Use       | Stock quotes, risk metrics, filings, fund screening      | Tool trajectory match       |
| Conversation   | Multi-turn: portfolio advice, due diligence, risk        | LLM-as-judge                |
| Analysis       | DCF, LBO modeling, ratio analysis, deal structuring      | Regex/numeric match + judge |
| Compliance     | SEC rules, AML/KYC, fiduciary duty, Dodd-Frank          | Exact/regex match + judge   |

## Usage

### CLI

```bash
# Run all benchmarks on all proxy models
python main.py run

# Run specific categories
python main.py run -c reasoning,math

# Benchmark specific models
python main.py benchmark -m gpt-4o,claude-sonnet-4-5

# List available models
python main.py models

# List categories
python main.py categories

# Generate report from previous results
python main.py report --format html --output results.html

# Interactive agent mode
python main.py agent
```

### Streamlit Dashboard

```bash
streamlit run app.py
```

The dashboard provides four pages:

- **Dashboard** — Best model callout, leaderboard table, overall score chart
- **Run Benchmarks** — Category listing and CLI quick reference
- **Category Details** — Drill into per-task scores for any category
- **Public Comparison** — Side-by-side view with HF Open LLM Leaderboard scores

## Output Formats

| Format    | Description                                  |
|-----------|----------------------------------------------|
| CLI       | Rich colored tables with model rankings      |
| HTML      | Interactive report with Plotly charts         |
| CSV       | Flat export for spreadsheet analysis          |
| Streamlit | Interactive web dashboard with Plotly charts  |

## Project Structure

```
llm_benchmark_agent_V1/
├── app.py                         # Streamlit dashboard
├── main.py                        # CLI entry point
├── config.py                      # Settings loaded from .env
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
├── .gitignore
│
├── agent/
│   ├── orchestrator.py            # LangChain agent definition
│   └── tools.py                   # @tool-decorated benchmark tools
│
├── benchmarks/
│   ├── base.py                    # BaseBenchmark, BenchmarkTask, EvalMethod
│   ├── registry.py                # Auto-registers all benchmarks
│   ├── reasoning.py               # Reasoning tasks
│   ├── math_bench.py              # Math tasks
│   ├── code_generation.py         # Coding tasks
│   ├── summarization.py           # Summarization tasks
│   ├── classification.py          # Classification tasks
│   ├── knowledge_qa.py            # Knowledge Q&A
│   ├── tool_use.py                # Tool use / function calling
│   ├── conversation.py            # Multi-turn conversation
│   ├── financial_analysis.py      # Financial analysis (DCF, LBO, ratios)
│   └── regulatory_compliance.py   # Compliance (SEC, AML)
│
├── evaluation/
│   ├── scorer.py                  # Scoring engine
│   └── llm_judge.py               # LLM-as-judge evaluation
│
├── models/
│   ├── discovery.py               # Model discovery from LiteLLM proxy
│   └── runner.py                  # Model execution runner
│
├── reports/
│   ├── cli_report.py              # Rich CLI report
│   ├── html_report.py             # Jinja2 HTML report
│   └── csv_report.py              # CSV export
│
├── leaderboard/
│   └── public_scores.py           # HF Open LLM Leaderboard fetcher
│
└── data/
    └── results/                   # Saved JSON results (gitignored)
```

## Tech Stack

- **LangChain** — Agent orchestration and tool management
- **LiteLLM** — Unified LLM proxy interface
- **Streamlit** — Interactive web dashboard
- **Plotly** — Interactive charts and visualizations
- **Rich** — Beautiful CLI output
- **Click** — CLI framework
- **Pandas** — Data manipulation and analysis
- **Jinja2** — HTML report templating
