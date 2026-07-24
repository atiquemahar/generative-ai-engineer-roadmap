# experiments/day14_citations.py

import os
import sys
import json
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")  

# ── Structured output models ───────────────────────────────────────────────

class Citation(BaseModel):
    document: str
    chunk_index: int
    overlap_score: float # token overlap ratio — how much of answer appears in this chunk

class RAGResponse(BaseModel):
    answer: str
    supported: bool
    confidence: Literal["high", "medium", "low"] 
    citations: list[Citation]
    unanswerable_reason: Optional[str] = None  

# ── Citation RAG Pipeline ──────────────────────────────────────────────────

class CitationRAGPipeline:
    def __init__(self, vectorstore: FAISS, client: AzureOpenAI, model_name: str):
        self.vectorstore = vectorstore
        self.client = client
        self.model_name = model_name

    def retrieve(self, query: str, k: int =3):
        return self.vectorstore.similarity_search_with_score(query, k=k) 

    def build_context(self, doc_score_pairs: list) -> str:
        parts = []
        for i, (doc, score) in enumerate(doc_score_pairs, 1):
            filename = doc.metadata.get("filename", "unkown")
            parts.append(f"[{i}] Source: {filename} (score: {score:.3f})\n{doc.page_content}")
        return "\n\n".join(parts) 

    def is_grounded(self, answer: str, chunk_text: str, threshold: float =0.35) -> bool:
        """
        Deterministic grounding check — no LLM call.
        Measures what fraction of answer words appear in the chunk.
        threshold=0.35 means 35% of answer words must appear in chunk.
        """

        answer_words = set(answer.lower().split())   
        chunk_words = set(chunk_text.lower().split())

        # Remove stopwords — they inflate the score artificially
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "of",
                     "to", "in", "on", "at", "for", "and", "or", "but",
                     "not", "this", "that", "it", "with", "as", "by"}
        answer_words -= stopwords
        chunk_words -= stopwords

        if not answer_words:
            return False

        overlap = len(answer_words & chunk_words) / len(answer_words)
        return overlap >= threshold

    def compute_overlap_score(self, answer: str, chunk_text: str) -> float:
        """Return raw overlap ratio for citation scoring."""
        answer_words = set(answer.lower().split())
        chunk_words = set(chunk_text.lower().split())
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "of",
                     "to", "in", "on", "at", "for", "and", "or", "but",
                     "not", "this", "that", "it", "with", "as", "by"}
        answer_words -= stopwords
        if not answer_words:
            return 0.0
        return len(answer_words & (chunk_words - stopwords)) / len(answer_words) 

    def answer_with_citations(self, query: str) -> RAGResponse:
        """
        Full RAG pipeline with structured citations.
        Never fabricates a citation — only cites retrieved chunks.
        """
        doc_score_pairs = self.retrieve(query)

        if not doc_score_pairs:
            return RAGResponse(
                answer="I don't have enough information to answer this question.",
                supported=False,
                confidence="low",
                citations=[],
                unanswerable_reason="No relevant documents retrieved"
            )
        context = self.build_context(doc_score_pairs)

        system_prompt = """You are a helpful HR and policy assistant for NovaTech Enterprises.
        Answer questions based ONLY on the provided context documents.
        If the context does not contain enough information, say exactly:
        "I don't have enough information in the provided documents to answer this question."
        Never fabricate information. Quote exact figures when available."""

        user_input = f"""Context documents: {context}
                        
        Question: {query}

        Answer based only on the context above."""

        response = self.client.responses.create(
            model=self.model_name,
            instructions=system_prompt,
            input=user_input,
            max_output_tokens=500,
        )

        answer = response.output_text.strip()

        # Grounding check — deterministic
        no_info_phrases = ["i don't have enough information", "cannot answer"]
        is_unanswerable = any(p in answer.lower() for p in no_info_phrases)

        if is_unanswerable:
            return RAGResponse(
                answer=answer,
                supported=False,
                confidence="low",
                citations=[],
                unanswerable_reason="Model could not find answer in retrieved context"
            )

        # Build citations — only from retrieved chunks, never fabricated
        citations = []
        grounded_in_any = 0

        for i, (doc, retrieval_score) in enumerate(doc_score_pairs):
            overlap = self.compute_overlap_score(answer, doc.page_content)
            if overlap > 0.1: # only cite chunks with meaningful overlap
                citations.append(Citation(
                    document=doc.metadata.get("filename", "unkown"),
                    chunk_index=i,
                    overlap_score=round(overlap, 3)
                ))
                if self.is_grounded(answer, doc.page_content):
                    grounded_in_any = True

        # Confidence based on grounding and citation count
        if grounded_in_any and len(citations)  >= 2:
            confidence = "high"
        elif grounded_in_any or len(citations) >= 1:
            confidence = "medium"
        else:
            confidence = "low" 

        return RAGResponse(
            answer=answer,
            supported=grounded_in_any or len(citations) > 0,
            confidence= confidence,
            citations=citations,
        )  

# ── Load pipeline ──────────────────────────────────────────────────────────

def loadPipeline() -> CitationRAGPipeline:
    index_path = Path(REPO_ROOT) / "experiments" / "retrieval" / "faiss_index"

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version="2025-04-01-preview",
    ) 

    vectorstore = FAISS.load_local(
        str(index_path), embeddings=embeddings, allow_dangerous_deserialization= True
    )

    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version="2025-04-01-preview",
    )  
    model_name =os.environ["MODEL_DEPLOYMENT_NAME"]

    return CitationRAGPipeline(vectorstore, client, model_name)

# ── Test cases ─────────────────────────────────────────────────────────────

ANSWERABLE = [
    "What is the maximum expense claim without a receipt?",
    "How many days of annual leave does a new employee get?",
    "What uptime percentage does the vendor guarantee for production workloads?",
    "What is the response SLA for a P1 Critical IT incident?",
    "How many Keeping in Touch days can an employee work during parental leave?",
]

UNANSWERABLE = [
    "What is the CEO's salary at NovaTech?",
    "How many employees does NovaTech have globally?",
    "What is the company's revenue target for 2027?",
    "Who is the head of the IT department?",
    "What is NovaTech's stock ticker symbol?",
]

if __name__ == "__main__":
    print("Loading pipeline...")
    pipeline = loadPipeline()
    print("Ready.\n")

    # ── Answerable questions ───────────────────────────────────────────────
    print("=" * 70)
    print("ANSWERABLE QUESTIONS — Citations must be present")
    print("=" * 70)

    citation_errors = []    # citations pointing to non-retrieved docs

    answerable_results = []
    for i, question in enumerate(ANSWERABLE, 1):
        result = pipeline.answer_with_citations(question)
        answerable_results.append(result)

        print(f"\n[{i}] Q: {question}")
        print(f"     A: {result.answer[:120]}...")
        print(f"     Supported: {result.supported} | Confidence: {result.confidence}")
        print(f"     Citations ({len(result.citations)}):")

        for c in result.citations:
            print(f"       - {c.document} | chunk {c.chunk_index} | overlap {c.overlap_score:.3f}")

        # Verify: no citation fabricated
        if result.supported and not result.citations:
            citation_errors.append(f"Q{i}: supported=True but no citations")

    # ── Unanswerable questions ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("UNANSWERABLE QUESTIONS — supported must be False")
    print("=" * 70)

    unanswerable_results = []
    refusal_score = 0
    for i, question in enumerate(UNANSWERABLE, 1):
        result = pipeline.answer_with_citations(question)
        unanswerable_results.append(result)
        correct_refusal = not result.supported
        if correct_refusal:
            refusal_score += 1
        status = "✓" if correct_refusal else "✗"
        print(f"[{i}] {status} {question[:60]}")
        if not correct_refusal:
            print(f"     ⚠ Expected supported=False, got: {result.answer[:80]}...")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Refusal accuracy (unanswerable): {refusal_score}/{len(UNANSWERABLE)}")
    if citation_errors:
        print(f"Citation errors: {len(citation_errors)}")
        for err in citation_errors:
            print(f"  - {err}")
    else:
        print("Citation integrity: ✓ No fabricated citations")


    # ── Save ──────────────────────────────────────────────────────────────
    # Then save from stored results — no second model call
    all_results = []
    for q, r in zip(ANSWERABLE + UNANSWERABLE, answerable_results + unanswerable_results):
        all_results.append({
            "question": q,
            "answer": r.answer,
            "supported": r.supported,
            "confidence": r.confidence,
            "citations": [c.model_dump() for c in r.citations],
            "unanswerable_reason": r.unanswerable_reason,
        })

    output_path = Path(REPO_ROOT) / "experiments" / "day14_citation_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {output_path}")            


        

