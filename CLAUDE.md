# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python tool that scrapes Barclaycard US FAQ pages with Playwright, parses Q&A pairs from HTML, and serves them through a Streamlit chatbot backed by OpenAI embeddings + FAISS vector search.

## Setup & Commands

```bash
# First-time setup (installs deps + Playwright chromium)
bash setup.sh

# Add OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# Run the Streamlit chatbot (main entry point)
uv run streamlit run app.py

# Re-scrape FAQs from Barclaycard (writes faqs.json + faqs.jsonl)
uv run python faq_parser.py

# Quick parse demo with console preview
uv run python example.py

# Use parsed FAQs programmatically with LangChain
uv run python rag_integration.py
```

There are no tests or linting configured in this project.

After re-scraping, delete `vectorstore/` so `app.py` rebuilds the FAISS index with fresh data.

## Architecture

**`app.py`** — Streamlit chatbot (main entry point)
- `load_vectorstore()`: builds a FAISS index from `faqs.jsonl` using `text-embedding-3-small` on first run, then loads from `vectorstore/` on subsequent runs. Cached with `@st.cache_resource`.
- `build_qa_chain()`: wraps a `RetrievalQA` chain (from `langchain_classic`) with `gpt-4o-mini`, retrieving top-4 FAQ chunks per question.
- Renders a persistent chat history in `st.session_state.messages` and shows an expandable "Sources" expander under each answer.
- Reads `OPENAI_API_KEY` from `.env` via `python-dotenv`.

**`faq_parser.py`** — scraping and parsing
- `FAQParser` uses Playwright (async Chromium) to fetch JS-rendered pages.
- `parse_faq_content()` runs 6 strategies in priority order, short-circuiting on first match:
  0. `_parse_barclays_accordions` — `li.bcus-accordion__container` → `h2.bcus-accordion__header` + `span.bcus-accordion__content`
  1. Class-based: `.faq-item`, `.faq-entry`, `.question-answer`
  2. Generic accordion: `[role="tablist"]`, `.accordion`, `.collapse`
  3. Definition lists: `<dl>/<dt>/<dd>`
  4. Heading+paragraph: `<h3>`/`<h4>` followed by `<p>`
  5. Semantic divs: `[data-qa]` with `[role]`
- Writes `debug_page.html` on every run — inspect this when parsing yields no results.
- Hardcoded target URL lives in `main()` — change it there or call `parser.parse_url(url)` directly.

**`rag_integration.py`** — optional LangChain bridge
- `FAQRAGIntegration` reads `faqs.jsonl` → `langchain_core.documents.Document` objects.
- `prepare_for_vectorstore()` chunks with `RecursiveCharacterTextSplitter` (default 512 tokens, 50 overlap).
- Not used by `app.py` directly; useful for integrating with external vector stores or LLM frameworks.

**Data model (`QAPair` in `faq_parser.py`)**
- Fields: `question`, `answer`, `source_url`, `category` (optional), `extracted_at` (ISO timestamp).
- Pydantic v2 — use `.model_dump()` / `.model_dump_json()`.

## Key Details

- **LangChain version**: 1.x — `RetrievalQA` is in `langchain_classic.chains`, not `langchain.chains`. `PromptTemplate` is in `langchain_core.prompts`.
- **Vector store**: FAISS index persisted to `vectorstore/`. Delete this directory to force a rebuild.
- **`FAQParser` params**: `headless` (default `True`), `timeout` in ms (default `60000`), `max_retries` (default `2`) with exponential backoff.
- **Package manager**: `uv` — use `uv sync` and `uv run`. `requirements.txt` exists as a pip fallback only.
