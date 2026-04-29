# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python tool that scrapes FAQ pages (originally targeting Barclaycard US) using Playwright for JS-rendered content, parses Q&A pairs from HTML, and outputs them in JSON/JSONL format for RAG pipelines.

## Setup & Commands

```bash
# First-time setup (installs deps + Playwright chromium)
bash setup.sh

# Or manually
uv sync
uv run playwright install chromium

# Run the parser (fetches Barclaycard FAQ, writes faqs.json + faqs.jsonl)
uv run python faq_parser.py

# Quick demo with preview output
uv run python example.py

# Load parsed FAQs for RAG integration (requires langchain to be installed separately)
uv run python rag_integration.py
```

There are no tests or linting configured in this project.

## Architecture

The project has three layers:

**`faq_parser.py`** — core scraping and parsing logic
- `FAQParser` uses Playwright (async Chromium) to fetch dynamically rendered pages
- `parse_faq_content()` runs 6 parsing strategies in priority order, short-circuiting on first match:
  0. `_parse_barclays_accordions` — site-specific: `li.bcus-accordion__container` with `h2.bcus-accordion__header` + `span.bcus-accordion__content`
  1. Class-based: `.faq-item`, `.faq-entry`, `.question-answer`
  2. Generic accordion: `[role="tablist"]`, `.accordion`, `.collapse`
  3. Definition lists: `<dl>/<dt>/<dd>`
  4. Heading+paragraph: `<h3>`/`<h4>` followed by `<p>`
  5. Semantic divs: `[data-qa]` with `[role]`
- Output is `QAPair` Pydantic v2 models saved as `faqs.json` (formatted) and `faqs.jsonl` (one record per line)
- `debug_page.html` is written on each run — useful for inspecting raw fetched HTML when parsing fails

**`rag_integration.py`** — LangChain bridge (optional)
- `FAQRAGIntegration` reads `faqs.jsonl` and converts records into `langchain_core.documents.Document` objects
- `prepare_for_vectorstore()` chunks documents with `RecursiveCharacterTextSplitter` (default 512 tokens, 50 overlap)
- LangChain is not in `pyproject.toml`; install separately: `uv pip install langchain langchain-text-splitters`

**Data model (`QAPair`)**
- Fields: `question`, `answer`, `source_url`, `category` (optional), `extracted_at` (ISO timestamp)
- Pydantic v2 — use `.model_dump()` / `.model_dump_json()`

## Key Details

- The hardcoded target URL is in `main()` inside `faq_parser.py`. To parse a different site, pass a custom URL to `parser.parse_url(url)`.
- `FAQParser` accepts `headless`, `timeout` (ms, default 60000), and `max_retries` (default 2). Retries use exponential backoff (2s × attempt).
- Playwright launches a new browser context per retry attempt and always closes it in the `finally` block.
- Package manager is `uv`; `requirements.txt` exists as a pip fallback but `uv sync` from `pyproject.toml` is preferred.