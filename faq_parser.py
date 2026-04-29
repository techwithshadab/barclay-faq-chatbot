"""
FAQ Parser for RAG Chatbot
Parses FAQs from websites and extracts Q&A pairs in structured format
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field

from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from loguru import logger


# Configure logging
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)


class QAPair(BaseModel):
    """Q&A pair model for RAG chatbot"""
    question: str = Field(..., description="FAQ question")
    answer: str = Field(..., description="FAQ answer")
    source_url: str = Field(..., description="URL where Q&A was found")
    category: Optional[str] = Field(default=None, description="FAQ category if available")
    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How do I reset my password?",
                "answer": "Visit the login page and click 'Forgot Password'...",
                "source_url": "https://example.com/faqs",
                "category": "Account Management",
                "extracted_at": "2024-01-15T10:30:00"
            }
        }


class FAQParser:
    """Parse FAQs from websites with dynamic content support"""

    def __init__(self, headless: bool = True, timeout: int = 60000, max_retries: int = 2):
        self.headless = headless
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def fetch_page(self, url: str) -> tuple[str, str]:
        """Fetch page content using Playwright for dynamic content support"""
        for attempt in range(self.max_retries):
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    ignore_https_errors=True,
                    extra_http_headers={"Accept-Language": "en-US"}
                )
                page = await context.new_page()

                try:
                    logger.info(f"Fetching URL: {url} (attempt {attempt + 1}/{self.max_retries})")

                    # Try load first, fallback to domcontentloaded on timeout
                    try:
                        await page.goto(url, wait_until="load", timeout=self.timeout)
                    except Exception:
                        logger.warning("Load timeout, falling back to domcontentloaded")
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    # Wait a bit for JavaScript to render FAQ content
                    await page.wait_for_timeout(2000)

                    # Try to wait for FAQ container if it exists
                    try:
                        await page.wait_for_selector(
                            "[class*='bcus-accordion'], [class*='accordionitem'], [class*='faq'], [class*='accordion'], dl, [role='tablist']",
                            timeout=5000
                        )
                    except Exception:
                        # Page might not have typical FAQ selectors, continue anyway
                        logger.warning("Could not find typical FAQ selectors, proceeding with page content")

                    # Get page content
                    content = await page.content()
                    title = await page.title()

                    logger.success(f"Successfully fetched page: {title}")
                    return content, url

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed to fetch page after {self.max_retries} attempts")
                        raise
                    await page.wait_for_timeout(2000 * (attempt + 1))  # Exponential backoff
                finally:
                    await browser.close()

    def parse_faq_content(self, html_content: str, source_url: str) -> list[QAPair]:
        """
        Parse FAQ content from HTML
        Supports multiple FAQ formats
        """
        soup = BeautifulSoup(html_content, "html.parser")
        qa_pairs = []

        # Strategy 0: Check for Barclays-specific accordion format first
        barclays_qa = self._parse_barclays_accordions(soup, source_url)
        if barclays_qa:
            logger.info(f"Found {len(barclays_qa)} FAQ items using Barclays accordion format")
            qa_pairs.extend(barclays_qa)

        # Strategy 1: Look for common FAQ patterns with data attributes
        if not qa_pairs:
            faq_items = soup.find_all(class_=["faq-item", "faq-entry", "question-answer"])
            if faq_items:
                logger.info(f"Found {len(faq_items)} FAQ items using class selectors")
                qa_pairs.extend(
                    self._parse_faq_items_by_class(faq_items, source_url)
                )

        # Strategy 2: Look for accordion patterns
        if not qa_pairs:
            accordions = soup.find_all(
                ["div", "section"],
                attrs={"role": "tablist"}
            ) or soup.find_all(
                class_=["accordion", "collapse", "tabs"]
            )
            if accordions:
                logger.info(f"Found accordion patterns, parsing...")
                qa_pairs.extend(self._parse_accordions(accordions, source_url))

        # Strategy 3: Look for dt/dd patterns (definition lists)
        if not qa_pairs:
            dl_items = soup.find_all("dl")
            if dl_items:
                logger.info(f"Found definition list patterns")
                qa_pairs.extend(self._parse_definition_lists(dl_items, source_url))

        # Strategy 4: Look for h3/h4 + paragraph patterns
        if not qa_pairs:
            qa_pairs.extend(self._parse_heading_paragraph_pattern(soup, source_url))

        # Strategy 5: Look for divs with data-qa or aria-label attributes
        if not qa_pairs:
            qa_pairs.extend(self._parse_semantic_divs(soup, source_url))

        logger.info(f"Successfully extracted {len(qa_pairs)} Q&A pairs")
        return qa_pairs

    def _parse_faq_items_by_class(
        self, items: list, source_url: str
    ) -> list[QAPair]:
        """Parse FAQ items marked with FAQ classes"""
        qa_pairs = []
        for item in items:
            question_elem = item.find(
                ["h2", "h3", "h4", "span", "div"],
                class_=["question", "faq-question", "q"]
            )
            answer_elem = item.find(
                ["p", "div"],
                class_=["answer", "faq-answer", "a"]
            )

            if question_elem and answer_elem:
                question = question_elem.get_text(strip=True)
                answer = answer_elem.get_text(strip=True)

                if question and answer and len(question) > 5:
                    category = self._extract_category(item)
                    qa_pairs.append(
                        QAPair(
                            question=question,
                            answer=answer,
                            source_url=source_url,
                            category=category
                        )
                    )

        return qa_pairs

    def _parse_accordions(self, accordions: list, source_url: str) -> list[QAPair]:
        """Parse accordion/collapsible content"""
        qa_pairs = []
        for accordion in accordions:
            # Find all accordion items/panels
            items = accordion.find_all(
                ["div", "li", "button"],
                recursive=True,
                limit=None
            )

            for item in items:
                # Look for button/heading (question)
                button = item.find(["button", "a"], class_=["accordion-button", "btn-link"]) or item.find("button")
                # Look for hidden/expanded content (answer)
                content = item.find(["div", "section"], class_=["collapse", "accordion-body", "content"])

                if button and content:
                    question = button.get_text(strip=True)
                    answer = content.get_text(strip=True)

                    if question and answer and len(question) > 5:
                        qa_pairs.append(
                            QAPair(
                                question=question,
                                answer=answer,
                                source_url=source_url
                            )
                        )

        return qa_pairs

    def _parse_barclays_accordions(self, soup: BeautifulSoup, source_url: str) -> list[QAPair]:
        """Parse Barclays-specific accordion format (bcus-accordion__container)"""
        qa_pairs = []

        # Find all Barclays accordion containers (they're LI elements!)
        containers = soup.find_all("li", class_=lambda x: x and "bcus-accordion__container" in x)
        logger.info(f"Found {len(containers)} Barclays accordion items")

        for container in containers:
            # Question is in h2 with bcus-accordion__header class
            header = container.find("h2", class_="bcus-accordion__header")
            if not header:
                continue

            # Content is in span with bcus-accordion__content class
            content_span = container.find("span", class_="bcus-accordion__content")
            if not content_span:
                continue

            question = header.get_text(strip=True)
            answer = content_span.get_text(strip=True)

            # Filter out noise
            if question and answer and len(question) > 3 and len(answer) > 10:
                qa_pairs.append(
                    QAPair(
                        question=question,
                        answer=answer,
                        source_url=source_url
                    )
                )

        return qa_pairs

    def _parse_definition_lists(self, dls: list, source_url: str) -> list[QAPair]:
        """Parse definition list (dt/dd) patterns"""
        qa_pairs = []
        for dl in dls:
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")

            for dt, dd in zip(dts, dds):
                question = dt.get_text(strip=True)
                answer = dd.get_text(strip=True)

                if question and answer and len(question) > 5:
                    qa_pairs.append(
                        QAPair(
                            question=question,
                            answer=answer,
                            source_url=source_url
                        )
                    )

        return qa_pairs

    def _parse_heading_paragraph_pattern(
        self, soup: BeautifulSoup, source_url: str
    ) -> list[QAPair]:
        """Parse heading followed by paragraph pattern"""
        qa_pairs = []
        headings = soup.find_all(["h3", "h4", "h5"])

        for heading in headings:
            # Look for following paragraph
            next_elem = heading.find_next()
            if next_elem and next_elem.name in ["p", "div"]:
                question = heading.get_text(strip=True)
                answer = next_elem.get_text(strip=True)

                # Filter out noise
                if (
                    question and answer
                    and len(question) > 5
                    and len(answer) > 10
                    and not question.lower() in ["related", "back to top"]
                ):
                    qa_pairs.append(
                        QAPair(
                            question=question,
                            answer=answer,
                            source_url=source_url
                        )
                    )

        return qa_pairs

    def _parse_semantic_divs(self, soup: BeautifulSoup, source_url: str) -> list[QAPair]:
        """Parse divs with semantic attributes"""
        qa_pairs = []

        # Look for elements with data-qa or aria-label
        items = soup.find_all(
            "div",
            attrs={
                "data-qa": True,
                "role": ["button", "heading", "tab"]
            }
        )

        for item in items:
            question = item.get("aria-label") or item.get_text(strip=True)
            # Look for sibling or child content
            answer_elem = item.find_next(["p", "div"])

            if answer_elem:
                answer = answer_elem.get_text(strip=True)
                if question and answer and len(question) > 5:
                    qa_pairs.append(
                        QAPair(
                            question=question,
                            answer=answer,
                            source_url=source_url
                        )
                    )

        return qa_pairs

    def _extract_category(self, element) -> Optional[str]:
        """Extract category from element or ancestors"""
        section = element.find_parent("section")
        if section:
            heading = section.find(["h2", "h3"])
            if heading:
                return heading.get_text(strip=True)

        # Check for category class
        for cls in element.get("class", []):
            if "category" in cls.lower() or "section" in cls.lower():
                return cls

        return None

    async def parse_url(self, url: str) -> list[QAPair]:
        """Main method to parse FAQs from URL"""
        try:
            html_content, source_url = await self.fetch_page(url)
            qa_pairs = self.parse_faq_content(html_content, source_url)
            return qa_pairs
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            raise

    def save_to_json(self, qa_pairs: list[QAPair], output_file: str = "faqs.json"):
        """Save Q&A pairs to JSON file"""
        output_path = Path(output_file)
        data = [qa.model_dump() for qa in qa_pairs]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.success(f"Saved {len(qa_pairs)} Q&A pairs to {output_path}")
        return output_path

    def save_to_jsonl(self, qa_pairs: list[QAPair], output_file: str = "faqs.jsonl"):
        """Save Q&A pairs to JSONL format (one JSON per line) for RAG systems"""
        output_path = Path(output_file)

        with open(output_path, "w", encoding="utf-8") as f:
            for qa in qa_pairs:
                f.write(qa.model_dump_json() + "\n")

        logger.success(f"Saved {len(qa_pairs)} Q&A pairs to {output_path}")
        return output_path


async def main():
    """Main execution"""
    # URL to parse
    url = "https://cards.barclaycardus.com/banking/help-center/faqs/general-additional-information/"

    # Initialize parser with increased timeout
    parser = FAQParser(headless=True, timeout=60000, max_retries=2)

    try:
        # Parse FAQs
        logger.info("Starting FAQ extraction...")

        # Fetch and save HTML for inspection
        html_content, _ = await parser.fetch_page(url)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("Saved HTML to debug_page.html for inspection")

        qa_pairs = parser.parse_faq_content(html_content, url)

        # Display results
        logger.info(f"\n{'='*60}")
        logger.info(f"Extracted {len(qa_pairs)} Q&A pairs")
        logger.info(f"{'='*60}\n")

        for i, qa in enumerate(qa_pairs[:5], 1):  # Show first 5
            print(f"\n[{i}] Q: {qa.question}")
            print(f"    A: {qa.answer[:100]}..." if len(qa.answer) > 100 else f"    A: {qa.answer}")
            if qa.category:
                print(f"    Category: {qa.category}")

        if len(qa_pairs) > 5:
            print(f"\n... and {len(qa_pairs) - 5} more Q&A pairs")

        # Save results
        logger.info(f"\n{'='*60}")
        json_path = parser.save_to_json(qa_pairs)
        jsonl_path = parser.save_to_jsonl(qa_pairs)

        logger.info(f"Files saved:")
        logger.info(f"  - JSON: {json_path}")
        logger.info(f"  - JSONL: {jsonl_path}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
