# Barclaycard FAQ Chatbot

A Python tool that scrapes FAQ pages from Barclaycard US, parses Q&A pairs, and serves them through a Streamlit chatbot powered by OpenAI and FAISS vector search.

## Stack

- **Playwright** — dynamic JS-rendered page fetching
- **BeautifulSoup4** — HTML parsing
- **Pydantic** — data validation
- **OpenAI** — embeddings (`text-embedding-3-small`) + chat (`gpt-4o-mini`)
- **FAISS** — local vector store for similarity search
- **LangChain** — retrieval chain orchestration
- **Streamlit** — chat UI
- **uv** — package management

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An OpenAI API key

## Setup

```bash
# Install dependencies + Playwright browser
bash setup.sh

# Create .env file with your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env
```

## Running the Chatbot

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`. On first launch, it builds a FAISS vector index from `faqs.jsonl` and saves it to `vectorstore/` — subsequent launches skip this step.

## Re-scraping FAQs

To refresh the FAQ data from Barclaycard:

```bash
uv run python faq_parser.py
```

Saves results to `faqs.json` (formatted) and `faqs.jsonl` (one record per line). Delete the `vectorstore/` directory afterwards so the app rebuilds the index with fresh data.

## Parsing a Custom URL

```python
import asyncio
from faq_parser import FAQParser

async def parse_custom():
    parser = FAQParser(headless=True, timeout=60000)
    qa_pairs = await parser.parse_url("https://your-faq-page.com")
    parser.save_to_json(qa_pairs, "custom_faqs.json")
    parser.save_to_jsonl(qa_pairs, "custom_faqs.jsonl")

asyncio.run(parse_custom())
```

## Data Model

```python
class QAPair(BaseModel):
    question: str
    answer: str
    source_url: str
    category: Optional[str]
    extracted_at: str        # ISO timestamp
```

## Parsing Strategies

`parse_faq_content()` tries strategies in order, stopping at the first match:

0. **Barclays accordion** — `li.bcus-accordion__container` (site-specific)
1. **Class-based** — `.faq-item`, `.faq-entry`, `.question-answer`
2. **Generic accordion** — `[role="tablist"]`, `.accordion`, `.collapse`
3. **Definition lists** — `<dl>/<dt>/<dd>`
4. **Heading+paragraph** — `<h3>`/`<h4>` followed by `<p>`
5. **Semantic divs** — `[data-qa]` with `[role]`

## Troubleshooting

**No Q&A pairs extracted?**
- Inspect `debug_page.html` (written on every `faq_parser.py` run) to see the raw fetched HTML
- Increase timeout: `FAQParser(timeout=90000)`

**Playwright browser issues?**
```bash
uv run playwright install chromium
```

**Chatbot not finding relevant answers?**
- Delete `vectorstore/` and restart the app to rebuild the index
- Ensure `faqs.jsonl` is populated by running `faq_parser.py` first

## License

MIT
