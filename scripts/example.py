"""
Quick start example - FAQ Parser
Run this to extract FAQs and see the results
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.parser.faq_parser import FAQParser


async def quick_demo():
    """Quick demo of FAQ parsing"""

    # Configuration
    url = "https://cards.barclaycardus.com/banking/help-center/faqs/general-additional-information/"

    # Create parser
    parser = FAQParser(headless=True)

    print("=" * 70)
    print("FAQ PARSER - Quick Demo")
    print("=" * 70)
    print(f"\nTarget URL: {url}\n")

    try:
        # Parse the FAQs
        print("⏳ Fetching and parsing FAQs...")
        qa_pairs = await parser.parse_url(url)

        # Display summary
        print(f"✅ Successfully extracted {len(qa_pairs)} Q&A pairs\n")

        # Show preview
        if qa_pairs:
            print("-" * 70)
            print("PREVIEW (First 3 Q&A pairs):")
            print("-" * 70)

            for i, qa in enumerate(qa_pairs[:3], 1):
                print(f"\n[{i}] QUESTION:")
                print(f"    {qa.question}")
                print(f"\n    ANSWER:")
                answer_preview = qa.answer[:150] + "..." if len(qa.answer) > 150 else qa.answer
                print(f"    {answer_preview}")
                if qa.category:
                    print(f"\n    CATEGORY: {qa.category}")

            remaining = len(qa_pairs) - 3
            if remaining > 0:
                print(f"\n\n... and {remaining} more Q&A pairs")

        # Save files
        print("\n" + "=" * 70)
        print("SAVING OUTPUT")
        print("=" * 70)

        json_file = parser.save_to_json(qa_pairs, "data/faqs.json")
        jsonl_file = parser.save_to_jsonl(qa_pairs, "data/faqs.jsonl")

        print(f"\n✓ JSON file: {json_file}")
        print(f"✓ JSONL file: {jsonl_file}")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("""
1. Review the extracted Q&A pairs in faqs.json or faqs.jsonl

2. Use with RAG systems:
   from rag_integration import FAQRAGIntegration
   rag = FAQRAGIntegration("faqs.jsonl")
   documents = rag.load_faqs()
   chunks = rag.prepare_for_vectorstore()

3. Integrate with your chatbot:
   - OpenAI/LangChain: Use with vector embeddings
   - Local LLMs: Use with Ollama or similar
   - Any RAG framework: JSONL format is universally compatible

4. Automate updates:
   - Schedule periodic runs with cron or GitHub Actions
   - Detect changes in new FAQs
   - Re-index embeddings as needed
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Check internet connection")
        print("- Ensure URL is accessible")
        print("- Try: uv run playwright install chromium")
        raise


if __name__ == "__main__":
    asyncio.run(quick_demo())
