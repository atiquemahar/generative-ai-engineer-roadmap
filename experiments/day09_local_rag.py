import os
import sys
import time
from dotenv import load_dotenv

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0,REPO_ROOT)

load_dotenv()

from shared.client_factory import get_openai_client

# Get client and model name — works with both Azure and OpenAI direct
client, model_name = get_openai_client()

documents = [
    {"id": "doc1", "content": "Our return policy allows returns within 30 days of purchase. Items must be unused and in original packaging", "source": "return-policy.txt"},
    {"id": "doc2", "content": "Shipments typically take 3-5 business days. Express shipping is available for an additional fee.", "source": "shipping-policy.txt"},
    {"id": "doc3", "content": "Refunds are processed within 7 business days after the returned item is received.", "source": "refund-policy.txt"},
    {"id": "doc4", "content": "Customer support is available Monday to Friday, 9am to 5pm. Contact us at support@example.com.", "source": "support-faq.txt"},
        {"id": "doc5", "content": "Products under warranty can be repaired or replaced free of charge within 12 months of purchase.", "source": "warranty-policy.txt"},
]

def keyword_retrieve(query: str, documents: list, top_k: int = 2) -> list:
    """
    Score documents by word overlap with query.
    Returns top_k documents sorted by score descending.
    Write this yourself — do not use any library.
    """
    query_words = set(query.lower().split())
    scored = []
    for doc in documents:
        doc_words = set(doc["content"].lower().split())
        overlap = len(query_words & doc_words)
        scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scored[:top_k] if score > 0]

def build_context(retrived_docs: list) -> str:
    """Format retrieved documents into a context string for the prompt."""
    if not retrived_docs:
        return "No relevant documnets found"
    parts = []
    for i, doc in enumerate(retrived_docs, 1):
        parts.append(f"[{i}] Source: {doc['source']}\n{doc['content']}")
    return "\n\n".join(parts)    

def rag_answer(query: str) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant documents
    2. Build context from retrieved docs
    3. Call model with context + query
    4. Return answer + sources
    """
    # step 1: Retrieve
    retrieved = keyword_retrieve(query, documents)

    # Step 2: Build context
    context = build_context(retrieved)
    sources = [doc['source'] for doc in retrieved]

    # Step 3: Generate — correct API pattern
    if not retrieved:
        return {
            "answer": "I don't have enough information to answer this question.",
            "sources": [],
            "supported": False,
            "context_used": ""
        }
    
    system_prompt = """You are a helpful assistant that answers questions based ONLY on the provided context.
        If the context does not contain enough information to answer the question, say so clearly.
        Never make up information not present in the context."""

    user_input = f"""Context:{context}
        Question: {query}
        Answer based only on the context above. If you cannot answer from the context, say "I don't have enough information."""

    
    response = client.responses.create(
        model=model_name,
        instructions=system_prompt,
        input=user_input,
        max_output_tokens=500,
        )
    return {
        "answer": response.output_text,
        "sources": sources,
        "supported": True,
        "context_used": context
    } 
   
# 10 test questions — write these yourself, covering all 5 documents
TEST_QUESTIONS = [
    "How long do I have to return a product?",
    "How long does shipping take?",
    "When will I receive my refund?",
    "How do I contact customer support?",
    "What does the warranty cover?",
    "Can I return a used item?",
    "Is express shipping available?",
    "What are support hours?",
    "How long is the warranty period?",
    "What happens if my product breaks?",
]

if __name__ == "__main__":
    print("Testing keyword RAG pipeline\n" + "="*50)
    failures = []

    for question in TEST_QUESTIONS:
        print(f"\nQ: {question}")
        result = rag_answer(question)
        print(f"A: {result['answer'][:150]}...")
        print(f"sources: {result['sources']}")
        if not result['supported']:
            failures.append({"question": question, "reason": "no documents retrieved"})
        time.sleep(1) 

    print(f"\n{'='*50}")
    print(f"Total questions: {len(TEST_QUESTIONS)}")
    print(f"Failures (no retrieval): {len(failures)}")

    # Save failures
    import json
    failures_path = os.path.join(os.path.dirname(__file__), "day09_failures.md")
    with open(failures_path, "w", encoding="utf-8") as f:
        f.write("# Day 09 — Keyword RAG Failures\n\n")
        f.write("## Questions That Failed Retrieval\n\n")
        for fail in failures:
            f.write(f"- **{fail['question']}** → {fail['reason']}\n")
        f.write("\n## Analysis\n\n")
        f.write("(Write your own analysis here — why did keyword matching fail on these inputs?)\n")

    print(f"Failures saved to: {failures_path}")       

