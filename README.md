# FAQ Parser for RAG Chatbot

A modern Python tool for parsing FAQs from websites into structured Q&A pairs for Retrieval-Augmented Generation (RAG) systems.

## Features

✨ **Multi-Format Support**
- Handles accordion patterns, definition lists, heading+paragraph structures
- Semantic HTML parsing with fallback strategies
- Extracts categories when available

🚀 **Modern Stack**
- **Playwright**: Dynamic content & JavaScript rendering support
- **BeautifulSoup4**: Robust HTML parsing
- **Pydantic**: Type-safe data validation
- **uv**: Fast Python package management

📦 **Output Formats**
- **JSON**: Human-readable, well-formatted
- **JSONL**: One Q&A per line, ideal for RAG systems and streaming

🔧 **RAG Integration**
- LangChain-compatible document format
- Automatic chunking for embeddings
- Metadata preservation (source, category, extraction time)

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

## Installation

### With uv (Recommended)

```bash
# Clone or navigate to project directory
cd Barclays

# Quick setup with script
bash setup.sh

# Or manual setup
uv sync
uv run playwright install chromium
```

### With pip

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

### Basic FAQ Extraction

```bash
uv run python faq_parser.py
```

This will:
1. Fetch the Barclaycard FAQ page
2. Parse Q&A pairs using multiple strategies
3. Save to `faqs.json` and `faqs.jsonl`

### Output Examples

**faqs.json** (formatted):
```json
[
  {
    "question": "How do I activate my card?",
    "answer": "You can activate your card through the mobile app or by calling...",
    "source_url": "https://cards.barclaycardus.com/banking/help-center/faqs/...",
    "category": "Card Activation",
    "extracted_at": "2024-01-15T10:30:00"
  }
]
```

**faqs.jsonl** (streaming format):
```
{"question": "...", "answer": "...", "source_url": "...", ...}
{"question": "...", "answer": "...", "source_url": "...", ...}
```

### Using with RAG Systems

```python
from rag_integration import FAQRAGIntegration

# Load FAQs
rag = FAQRAGIntegration(faq_file="faqs.jsonl")
documents = rag.load_faqs()

# Prepare for vector store
chunks = rag.prepare_for_vectorstore(chunk_size=512)

# Use with LangChain, LlamaIndex, etc.
# vectorstore.add_documents(chunks)
```

## Parsing Strategies

The parser uses multiple fallback strategies to handle different FAQ layouts:

1. **Class-based**: Looks for `.faq-item`, `.faq-entry`, `.question-answer` classes
2. **Accordion**: Parses collapsible/expandable content patterns
3. **Definition Lists**: Parses `<dt>` (question) / `<dd>` (answer) patterns
4. **Heading+Paragraph**: H3/H4 followed by paragraph content
5. **Semantic Divs**: Data attributes and ARIA labels for accessibility

## Advanced Configuration

### Parse Custom URL

```python
import asyncio
from faq_parser import FAQParser

async def parse_custom():
    parser = FAQParser(headless=True)
    url = "https://your-faq-page.com"
    qa_pairs = await parser.parse_url(url)
    parser.save_to_json(qa_pairs, "custom_faqs.json")

asyncio.run(parse_custom())
```

### Adjust Parsing Parameters

```python
parser = FAQParser(
    headless=True,      # Run browser in headless mode
    timeout=60000       # 60 second page load timeout
)
```

## Output Data Model

Each Q&A pair includes:

```python
class QAPair(BaseModel):
    question: str           # The FAQ question
    answer: str             # The FAQ answer
    source_url: str         # Source page URL
    category: Optional[str] # FAQ category if available
    extracted_at: str       # ISO timestamp of extraction
```

## Tips for RAG Integration

1. **Chunking**: JSONL format works best with streaming chunk processors
2. **Metadata**: Category and source_url are preserved as metadata for filtering
3. **Deduplication**: Check for duplicate questions after extraction
4. **Freshness**: Run extraction periodically to keep FAQs current
5. **Validation**: Review first few extracted Q&A pairs for accuracy

## Troubleshooting

**Page not loading?**
- Check internet connection
- Verify URL is accessible
- Increase timeout: `FAQParser(timeout=60000)`

**No Q&A pairs extracted?**
- The page structure might be unusual
- Add `logger.add(sys.stderr)` for debug output
- Inspect HTML manually to identify patterns

**Playwright browser issues?**
```bash
uv run playwright install chromium
```

## Performance

- **First run**: ~10-30 seconds (includes browser startup)
- **Subsequent runs**: ~5-15 seconds
- **Typical FAQ pages**: 20-100 Q&A pairs

## Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` | Dynamic content handling |
| `beautifulsoup4` | HTML parsing |
| `pydantic` | Data validation |
| `httpx` | Async HTTP (optional) |
| `loguru` | Logging |
| `python-dotenv` | Configuration (optional) |

## Use Cases

- 🤖 **Customer Service Bots**: FAQ-based chatbot training
- 📚 **Knowledge Bases**: Automated documentation collection
- 🔍 **RAG Systems**: Embedding-based search & retrieval
- 📊 **Data Analysis**: FAQ content analysis
- 📝 **Knowledge Management**: FAQ archiving and organization

## License

MIT

## Contributing

Improvements welcome! Consider:
- Adding support for more FAQ formats
- Improving category extraction
- Performance optimizations
- Additional output formats (CSV, Markdown)

---

**Questions?** Create an issue on GitHub or refer to the code comments for detailed implementation notes.
