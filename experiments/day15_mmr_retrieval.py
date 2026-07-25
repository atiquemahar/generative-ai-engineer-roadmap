# experiments/day14_citations.py

import os
import sys
import json
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
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
    retrieved_sources: list[str] = Field(default_factory=list)
    unanswerable_reason: Optional[str] = None  

# ── Citation RAG Pipeline ──────────────────────────────────────────────────

class CitationRAGPipeline:
    def __init__(self, vectorstore: FAISS, client: AzureOpenAI, model_name: str):
        self.vectorstore = vectorstore
        self.client = client
        self.model_name = model_name

    def retrieve(self, query: str, k: int = 5):
        docs = self.vectorstore.max_marginal_relevance_search(
        query,
        k=k,
        fetch_k=20,)
        return [(doc, 0.0) for doc in docs] 

    def build_context(self, doc_score_pairs: list) -> str:
        parts = []
        for i, (doc, score) in enumerate(doc_score_pairs, 1):
            filename = Path(doc.metadata.get("filename") or doc.metadata.get("source", "unknown")).name
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
        retrieved_sources = [
            Path(doc.metadata.get("filename")
            or doc.metadata.get("source", "unknown")).name
            for doc, _ in doc_score_pairs
        ]

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
            max_output_tokens=1000,
        )

        answer = response.output_text.strip()

        if not answer:
            return RAGResponse(
                answer="I don't have enough information in the provided documents to answer this question.",
                supported=False,
                confidence="low",
                citations=[],
                retrieved_sources=retrieved_sources,
                unanswerable_reason="Model returned empty response — possible timeout or content filter.",
            )

        # Grounding check — deterministic
        no_info_phrases = ["i don't have enough information", "cannot answer"]
        is_unanswerable = any(p in answer.lower() for p in no_info_phrases)

        if is_unanswerable:
            return RAGResponse(
                answer=answer,
                supported=False,
                confidence="low",
                citations=[],
                retrieved_sources=retrieved_sources,
                unanswerable_reason="Model could not find answer in retrieved context"
            )

        # Build citations — only from retrieved chunks, never fabricated
        citations = []
        grounded_in_any = 0

        for i, (doc, retrieval_score) in enumerate(doc_score_pairs):
            overlap = self.compute_overlap_score(answer, doc.page_content)
            if overlap > 0.1: # only cite chunks with meaningful overlap
                citations.append(Citation(
                    document=Path(doc.metadata.get("filename") or doc.metadata.get("source", "unkown")).name,
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
            retrieved_sources=retrieved_sources,
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
