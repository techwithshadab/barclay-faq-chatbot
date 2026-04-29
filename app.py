"""
Barclaycard FAQ Q&A Chatbot
Streamlit app powered by OpenAI + FAISS vector search over parsed FAQs
"""

import os
import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

load_dotenv()

FAQS_FILE = Path("data/faqs.jsonl")
VECTORSTORE_PATH = Path("data/vectorstore")

PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a helpful Barclaycard customer service assistant.
Use the FAQ excerpts below to answer the customer's question accurately and concisely.
If the answer isn't covered by the FAQs, say so clearly rather than guessing.

FAQ Context:
{context}

Customer Question: {question}

Answer:""",
)


@st.cache_resource(show_spinner="Building knowledge base from FAQs...")
def load_vectorstore() -> FAISS:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    if VECTORSTORE_PATH.exists():
        return FAISS.load_local(
            str(VECTORSTORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    if not FAQS_FILE.exists():
        st.error("data/faqs.jsonl not found. Run `uv run python src/parser/faq_parser.py` first.")
        st.stop()

    docs = []
    with open(FAQS_FILE, encoding="utf-8") as f:
        for line in f:
            qa = json.loads(line)
            content = f"Question: {qa['question']}\n\nAnswer: {qa['answer']}"
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": qa.get("source_url", ""),
                        "category": qa.get("category", ""),
                    },
                )
            )

    vs = FAISS.from_documents(docs, embeddings)
    vs.save_local(str(VECTORSTORE_PATH))
    return vs


@st.cache_resource(show_spinner=False)
def build_qa_chain(_vectorstore: FAISS) -> RetrievalQA:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    retriever = _vectorstore.as_retriever(search_kwargs={"k": 4})
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": PROMPT_TEMPLATE},
        return_source_documents=True,
    )


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Barclaycard FAQ Assistant",
    page_icon="💳",
    layout="centered",
)

st.title("💳 Barclaycard FAQ Assistant")
st.caption("Ask any question about your Barclaycard account.")

# ── Check API key ─────────────────────────────────────────────────────────────

if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not set. Add it to your `.env` file and restart.")
    st.stop()

# ── Load resources ────────────────────────────────────────────────────────────

vectorstore = load_vectorstore()
qa_chain = build_qa_chain(vectorstore)

# ── Chat history ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────

if question := st.chat_input("Ask a question about your Barclaycard..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Looking up answer..."):
            result = qa_chain.invoke({"query": question})
            answer = result["result"]
            sources = result.get("source_documents", [])

        st.markdown(answer)

        if sources:
            with st.expander("Sources", expanded=False):
                seen = set()
                for doc in sources:
                    snippet = doc.page_content[:200].replace("\n", " ")
                    if snippet not in seen:
                        seen.add(snippet)
                        st.markdown(f"- {snippet}…")

    st.session_state.messages.append({"role": "assistant", "content": answer})
