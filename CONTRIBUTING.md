# Contributing to OutreachPilot

Thank you for your interest in contributing to OutreachPilot! Whether you're fixing a bug, adding a feature, improving docs, or suggesting ideas — every contribution helps entrepreneurs find better conversations.

---

## Ways to Contribute

### Good First Issues

If you're new to the project, these are great starting points:

- **Add a Hacker News scanner** — Free API via `hn.algolia.com`, no auth needed
- **Add a Product Hunt scanner** — GraphQL API, requires developer token
- **Add a Dev.to scanner** — Public REST API, no auth needed
- **Add a Notion exporter** — Export signals to a Notion database
- **Add a Slack webhook exporter** — Post high-value signals to a Slack channel
- **Write tests** — We need tests for scanners, filters, analyzers, and storage
- **Improve AI prompts** — Better prompts = better suggestions
- **Fix typos or improve docs** — Always welcome

### Feature Development

Bigger features we'd love help with:

- **Web dashboard** (Phase 1) — FastAPI + Jinja2 + HTMX frontend
- **LiteLLM integration** — Support Claude, Ollama, Groq alongside OpenAI
- **Campaign management UI** — Kanban board for tracking signal engagement
- **Feedback loop** — Rate signal quality, use ratings to improve AI scoring
- **Scheduled scans** — APScheduler integration for cron-like recurring scans
- **Plugin system** — Entry-point based discovery for community scanners/exporters

### Reporting Bugs

Open an issue with:
1. What you expected to happen
2. What actually happened
3. Steps to reproduce
4. Your Python version and OS
5. Any relevant log output (run with `-v` for verbose logging)

### Suggesting Features

Open an issue with the `feature` label. Describe:
1. The problem you're trying to solve
2. Your proposed solution
3. Any alternatives you considered

---

## Development Setup

### Prerequisites

- Python 3.11 or newer
- Git

### Getting Started

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/outreachpilot.git
cd outreachpilot

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install in development mode with dev dependencies
pip install -e ".[dev]"

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (needed for integration tests)

# 5. Verify everything works
python -m outreachpilot --help
python -c "from outreachpilot.config import load_subreddits; print(f'OK: {len(load_subreddits())} subreddits')"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_filters/test_rule_filter.py

# Run tests matching a keyword
pytest -k "reddit"
```

### Code Quality

```bash
# Lint with ruff
ruff check outreachpilot/

# Auto-fix lint issues
ruff check --fix outreachpilot/

# Format code
ruff format outreachpilot/
```

---

## Project Structure

```
outreachpilot/
├── outreachpilot/           # Main package
│   ├── scanners/            # Platform scanners (Reddit, HN, etc.)
│   ├── analyzers/           # AI analysis engine
│   ├── filters/             # Signal filtering
│   ├── personas/            # Voice/tone engine
│   ├── exporters/           # Output adapters (Sheets, CSV, etc.)
│   ├── storage/             # Local file storage (JSON)
│   ├── routes/              # FastAPI route handlers (Phase 1)
│   ├── templates/           # Jinja2 HTML templates (Phase 1)
│   ├── scheduler/           # Scan scheduling (Phase 1)
│   ├── config.py            # Settings loader
│   ├── app.py               # FastAPI app factory
│   └── __main__.py          # CLI entry point
├── config/                  # YAML configuration files
├── data/                    # Runtime data (JSON files)
├── tests/                   # Test suite
└── docs/                    # Documentation
```

### Module Quick Guide

| Module | What to know |
|--------|-------------|
| `scanners/` | Each scanner implements the `Scanner` protocol. Add new platforms here. |
| `analyzers/` | AI pipeline: prompt building → LLM call → JSON parsing. Edit prompts in `pipeline.py`. |
| `filters/` | Rule-based filtering runs BEFORE AI. Zero cost. Add new filter types here. |
| `personas/` | Builds prompt blocks from `personality.yml`. Touch this to change how personality is injected. |
| `exporters/` | Each exporter implements the `Exporter` protocol. Add new outputs here. |
| `storage/` | All JSON file CRUD. Each data type has its own module. |
| `config.py` | Central config. Everything imports from here. |
| `__main__.py` | CLI orchestration. The scan loop lives here. |

---

## How to Add a New Scanner

This is one of the most impactful contributions. Here's a step-by-step guide:

### 1. Create the scanner file

```python
# outreachpilot/scanners/hackernews.py
import logging
import time

from outreachpilot.scanners.base import RawSignal, Reply, fetch_json
from outreachpilot.scanners import registry

logger = logging.getLogger(__name__)

HN_API = "https://hn.algolia.com/api/v1"


class HackerNewsScanner:
    name = "hackernews"

    def scan(self, targets: list[str], max_age_hours: int = 24) -> list[RawSignal]:
        """Scan HN for recent stories. Targets = search queries or 'front_page'."""
        signals = []
        # Your implementation here...
        # Use fetch_json() from base.py for HTTP with retries
        # Return list of RawSignal objects
        return signals


registry.register(HackerNewsScanner())
```

### 2. Register in the registry

Edit `outreachpilot/scanners/registry.py`:

```python
def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    _loaded = True
    from outreachpilot.scanners import reddit      # noqa: F401
    from outreachpilot.scanners import hackernews   # noqa: F401  <-- add this
```

### 3. Add CLI support

Edit `outreachpilot/__main__.py` to add a `--hackernews` flag and call the scanner.

### 4. Write tests

```python
# tests/test_scanners/test_hackernews.py
from outreachpilot.scanners.hackernews import HackerNewsScanner

def test_hackernews_scanner_has_name():
    scanner = HackerNewsScanner()
    assert scanner.name == "hackernews"

# Add more tests with mocked HTTP responses
```

### 5. Add config file (if needed)

```yaml
# config/hackernews.yml
queries:
  - "Show HN"
  - "Ask HN"
min_points: 5
```

---

## How to Add a New Exporter

### 1. Create the exporter file

```python
# outreachpilot/exporters/slack_webhook.py
import logging
import requests

logger = logging.getLogger(__name__)


class SlackWebhookExporter:
    name = "slack"

    def export(self, rows: list[dict], config: dict | None = None) -> None:
        webhook_url = (config or {}).get("webhook_url")
        if not webhook_url:
            logger.error("No webhook_url provided for Slack export")
            return

        for row in rows:
            if row.get("Engage?") != "Yes":
                continue
            text = f"*{row.get('Post title', '')}*\n{row.get('Summary', '')}\n<{row.get('Post link', '')}>"
            requests.post(webhook_url, json={"text": text})
            logger.info("Posted signal to Slack: %s", row.get("Post title", "")[:50])
```

### 2. Add CLI flag and usage in `__main__.py`

---

## Code Style

### General Guidelines

- **Python 3.11+** — Use modern syntax (type hints, `match`, `|` union types)
- **Line length** — 100 characters max (configured in `pyproject.toml`)
- **Formatting** — Run `ruff format` before committing
- **Linting** — Run `ruff check` and fix all issues
- **Type hints** — Add type hints to function signatures. No need for inline variable types unless ambiguous.
- **Logging** — Use `logging.getLogger(__name__)` instead of `print()`. Use appropriate levels:
  - `logger.debug()` — detailed diagnostic info
  - `logger.info()` — progress updates, key milestones
  - `logger.warning()` — recoverable issues
  - `logger.error()` — failures that affect output
- **Docstrings** — One-line docstrings for simple functions. Multi-line for complex ones. Don't add docstrings to trivially obvious functions.
- **No unnecessary comments** — Code should be self-documenting. Only comment on the "why", not the "what".

### Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal: prefix with `_`

### Import Order

1. Standard library
2. Third-party packages
3. Local imports (`from outreachpilot...`)

Separated by blank lines.

---

## Pull Request Process

### Before Submitting

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/hackernews-scanner
   ```

2. **Make your changes** — keep PRs focused on one thing

3. **Test your changes:**
   ```bash
   pytest
   ruff check outreachpilot/
   ```

4. **Verify the CLI still works:**
   ```bash
   python -m outreachpilot --help
   python -m outreachpilot scan --no-sheets  # quick test (if you have API keys)
   ```

### PR Guidelines

- **Keep PRs small and focused.** One feature, one bug fix, or one improvement per PR.
- **Write a clear description.** What does this change? Why? How can it be tested?
- **Add tests** for new functionality.
- **Update docs** if your change affects user-facing behavior.
- **Don't refactor unrelated code** in the same PR.

### PR Template

```markdown
## What

Brief description of the change.

## Why

The problem or need this addresses.

## How to Test

Steps to verify the change works:
1. ...
2. ...

## Checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check`)
- [ ] Docs updated (if applicable)
- [ ] No unrelated changes included
```

### Review Process

- PRs are reviewed within 48 hours (we aim for 24h)
- Feedback is about code quality, not personal preference
- Small nits are fixed by the maintainer when merging, not sent back for revision
- Approved PRs are squash-merged to keep `main` history clean

---

## Issue Labels

| Label | Description |
|-------|------------|
| `good first issue` | Great for newcomers |
| `help wanted` | We'd love a contribution here |
| `bug` | Something isn't working |
| `feature` | New functionality |
| `scanner` | New platform scanner |
| `exporter` | New output adapter |
| `ui` | Web dashboard related |
| `docs` | Documentation improvement |
| `performance` | Speed or resource optimization |

---

## Community

- **GitHub Issues** — Bug reports, feature requests, and discussions
- **Pull Requests** — Code contributions
- **Discussions** — Open-ended questions and ideas (when enabled)

### Code of Conduct

Be kind, be constructive, be helpful. We're building this for entrepreneurs who are trying to make something meaningful. Treat other contributors the way you'd want to be treated.

Specifically:
- Welcome newcomers — everyone starts somewhere
- Give constructive feedback — explain the "why" behind suggestions
- Assume good intent — text is easily misread
- Focus on the code, not the person
- No harassment, discrimination, or personal attacks

---

## Recognition

All contributors are recognized in the project:
- Significant contributions are highlighted in release notes
- Regular contributors may be invited as project maintainers

---

## Questions?

Open an issue with the `question` label, or start a discussion. We're happy to help you get started with your first contribution.

Thank you for helping make OutreachPilot better for every entrepreneur out there.
