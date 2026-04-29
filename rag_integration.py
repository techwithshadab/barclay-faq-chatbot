"""
Example RAG Integration with LangChain
Shows how to use extracted FAQs with a RAG system
"""

from pathlib import Path
import json
from typing import Optional

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    print("LangChain not installed. Install with: uv pip install langchain langchain-text-splitters")
    exit(1)


class FAQRAGIntegration:
    """Integrate parsed FAQs with RAG systems"""

    def __init__(self, faq_file: str = "faqs.jsonl"):
        self.faq_file = Path(faq_file)
        self.documents = []

    def load_faqs(self) -> list[Document]:
        """Load FAQs from JSONL file and convert to LangChain Documents"""
        if not self.faq_file.exists():
            raise FileNotFoundError(f"FAQ file not found: {self.faq_file}")

        documents = []
        with open(self.faq_file, "r", encoding="utf-8") as f:
            for line in f:
                qa = json.loads(line)
                # Combine Q&A into document content
                content = f"Question: {qa['question']}\n\nAnswer: {qa['answer']}"
                metadata = {
                    "source": qa.get("source_url"),
                    "category": qa.get("category"),
                    "type": "faq",
                    "extracted_at": qa.get("extracted_at")
                }
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

        self.documents = documents
        return documents

    def chunk_documents(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> list[Document]:
        """Split documents into chunks for embedding"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return splitter.split_documents(self.documents)

    def prepare_for_vectorstore(self, chunk_size: int = 512) -> list[Document]:
        """Prepare documents for vector store ingestion"""
        if not self.documents:
            self.load_faqs()

        chunks = self.chunk_documents(chunk_size=chunk_size)
        return chunks


if __name__ == "__main__":
    rag = FAQRAGIntegration()
    docs = rag.load_faqs()
    print(f"Loaded {len(docs)} FAQ documents")
    print(f"\nExample document:")
    print(f"Content: {docs[0].page_content[:200]}...")
    print(f"Metadata: {docs[0].metadata}")
