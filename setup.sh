#!/bin/bash
# setup.sh - Quick setup script for FAQ Parser

set -e

echo "🚀 Setting up FAQ Parser with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Install from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✓ uv found"

# Sync dependencies
echo "📦 Installing dependencies..."
uv sync

# Install Playwright browsers
echo "🌐 Installing Playwright browsers (this may take a moment)..."
uv run playwright install chromium

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  uv run python faq_parser.py              # Parse FAQs and save to JSON/JSONL"
echo "  uv run python rag_integration.py         # Load FAQs for RAG system"
echo ""
echo "Output files:"
echo "  - faqs.json   (formatted JSON with all Q&A pairs)"
echo "  - faqs.jsonl  (JSONL format, one Q&A per line, ideal for RAG)"
