# AutoDoc Agent

Enterprise auto-documentation agent powered by **LangGraph** multi-agent architecture. Generates comprehensive documentation from source code using LLMs with tool-calling, recursive delegation, and self-validation.

## Features

- **LangGraph agents:** 4 specialized agents (Orchestrator, Clustering, DocWriter, Synthesizer) with tool-calling and validation loops
- **Multi-language support:** Python, Java, JavaScript, TypeScript, C, C++, C#, Kotlin, Go, Rust
- **On-premises:** Runs fully on your network with local LLMs (Ollama, vLLM) or via LiteLLM Proxy
- **Architecture diagrams:** Auto-generated Mermaid diagrams (architecture, data-flow, sequence)
- **Module-aware:** LLM-driven clustering groups code into logical modules with interactive codebase exploration
- **Self-validating:** Validator agent checks generated docs for completeness, Mermaid syntax, and hallucinations
- **Recursive delegation:** Large modules are automatically split and documented by child agents
- **Batch processing:** Document 20+ repos in a single run
- **CI/CD ready:** Designed to run on every push via GitHub Actions, GitLab CI, or Jenkins
- **Static HTML output:** Browsable documentation site with sidebar navigation and search

## Quick Start

```bash
# Install
pip install -e .

# Configure (copy and edit .env)
cp .env.example .env

# Generate docs for a repo
autodoc generate /path/to/your/repo --output ./docs-output

# Batch mode (multiple repos)
autodoc batch repos.yaml --output ./docs-output
```

## Configuration

Set your LLM endpoint in `.env`:

```bash
# LiteLLM Proxy (recommended for enterprise)
LLM_PROVIDER=litellm_proxy
LLM_BASE_URL=http://your-litellm-proxy:4000
LLM_API_KEY=sk-your-key
LLM_MODEL=gpt-4o
```

Or for Ollama:

```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=dummy
LLM_MODEL=qwen3:72b
```

## Architecture

```
Source Code
  -> TreeSitter AST Parsing
  -> Dependency Graph (NetworkX)
  -> ClusteringAgent (tool-calling, interactive exploration)
  -> DocWriterAgent (tool-calling, recursive delegation)
  -> ValidatorAgent (structural + LLM validation)
  -> SynthesizerAgent (parent module synthesis)
  -> Overview Generation
  -> Markdown + Static HTML Site
```

### Agent System

| Agent | Role |
|-------|------|
| **Orchestrator** | Supervisor StateGraph coordinating the 8-phase pipeline |
| **ClusteringAgent** | Explores codebase with tools to produce optimal module groupings |
| **DocWriterAgent** | Generates per-module docs with tool access to source code and dependencies |
| **ValidatorAgent** | Checks completeness, Mermaid syntax, and hallucinated references |
| **SynthesizerAgent** | Creates parent module overviews from child documentation |

## CI/CD Integration

```yaml
# GitHub Actions example
on:
  push:
    branches: [main]

jobs:
  generate-docs:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: pip install autodoc-agent
      - run: autodoc generate . --output ./docs
      - run: rsync -av ./docs/ docs-server:/var/www/docs/${{ github.event.repository.name }}/
```
