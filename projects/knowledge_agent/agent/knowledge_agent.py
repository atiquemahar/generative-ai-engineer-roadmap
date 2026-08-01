"""
projects/knowledge_agent/agent/knowledge_agent.py
Day 20 — Answer Generation + Structured Citations
 
KnowledgeAgent combines:
  1. HybridSearcher  — retrieves chunks from Azure AI Search
  2. LLM generation  — answer + grounding decision via AIProjectClient
  3. Citation builder — built from retrieval results, NEVER from LLM output
 
Citation safety rule:
    The LLM is asked for: answer, supported, confidence.
    The LLM is NEVER asked for sources.
    _build_sources() constructs the sources list from the list[dict]
    returned by the searcher. This guarantees zero fabrication.
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from pathlib import Path
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(Path(REPO_ROOT) / ".env")

from projects.knowledge_agent.retrieval.searcher import HybridSearcher

MODEL_NAME = os.environ["MODEL_DEPLOYMENT_NAME"]

# ── System prompt ─────────────────────────────────────────────────────────────
# The LLM receives numbered context chunks and must return JSON with exactly
# three keys: answer, supported, confidence.
# It is deliberately NOT asked to list sources — that is Python's job.

SYSTEM_PROMPT = """
You are an enterprise knowledge assistant for NovaTech Enterprises.
Answer questions using ONLY the numbered context chunks provided below.
Do not use any knowledge outside the provided context.

Rules:
- supported: true if the context contains sufficient information to address
  the main intent of the question, even if spread across multiple chunks.
  When a question has multiple parts, answer each part you can find in the
  context. Set confidence="medium" if you can answer some parts but not all.
- supported: false ONLY if the context has NO relevant information about
  the question — not because a single chunk doesn't fully cover it.
- supported means the context must explicitly state the relevant information,
  not merely be topically related. Do not infer or assume policies not stated.
- confidence:
    "high"   — context directly and fully answers the question.
    "medium" — context partially answers it or requires minor inference.
    "low"    — context is tangentially related but doesn't clearly answer.
- When supported is false, set answer to exactly:
  "This information is not available in the provided documents."
- Never invent numbers, dates, names, or policy details not in the context.
- Keep your answer under 150 words. Cover all parts of the question concisely.
  Never pad, never truncate mid-sentence, never omit numbers or dates.
- Reference policy names or section headings when visible in the context.

Return ONLY valid JSON with exactly these three keys — no markdown, no preamble:
{
    "answer": "your answer here",
    "supported": true,
    "confidence": "high"
}
""".strip()

# ── KnowledgeAgent ────────────────────────────────────────────────────────────

class KnowledgeAgent:
    def __init__(self):
        self.searcher = HybridSearcher()
        self.openai_client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version="2025-04-01-preview",
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Format retrieved chunks as numbered blocks for the LLM prompt.
        Each block shows the source filename and content.
        The LLM sees filenames so it can refer to them in prose,
        but is NOT responsible for producing the citation list.
        """
        parts = []
        for i, chunk in enumerate(chunks, 1):
            filename = chunk.get("filename", "unkown")
            heading = chunk.get("heading", "")
            content = chunk.get("content", "")
            section = f" — {heading}" if heading else ""
            parts.append(f"[{i}] {filename}{section}\n{content}")
        return "\n\n".join(parts)

    def _build_sources(self, chunks: list[dict]) -> list[dict]:
        """
        Build the citation list from retrieval results only.
 
        Deduplicates by filename — multiple chunks from the same file
        collapse into one citation entry using the highest-scoring chunk
        as the representative. Sorted by relevance score descending.
 
        This is the only method that touches 'sources'.
        The LLM never does.
        """ 
        seen: dict[str, dict] = {}

        for chunk in chunks:
            filename = chunk.get("filename", "")
            if not filename:
                continue

            # Prefer reranker_score (0–4) when available, fall back to BM25/RRF score
            score = chunk.get("@search.reranker_score") or chunk.get("@search.score", 0.0)

            if filename not in seen:
                seen[filename] = chunk
            else:
                existing_score = (
                    seen[filename].get("@search.reranker_score")
                    or seen[filename].get("@search.score", 0.0)
                )
                if score > existing_score:
                    seen[filename] = chunk

        sources = []
        for filename, chunk in seen.items():
            score = chunk.get("@search.reranker_score") or chunk.get("@search.score", 0.0)
            sources.append({
                "document": filename,
                "page": chunk.get("page_number", 0),
                "section": chunk.get("heading", "") or "",
                "department": chunk.get("department", ""),
                "relevance_score": round(float(score), 4),
            })
        sources.sort(key=lambda s: s["relevance_score"], reverse=True) 
        return sources

    def _generate(self, question: str, context: str) -> dict:
        """
        Call the LLM via AIProjectClient (Foundry pattern).
        Returns parsed dict with answer, supported, confidence.
        Falls back gracefully on JSON parse failure.
        """
    
        response = self.openai_client.responses.create(
            model=MODEL_NAME,
            instructions=SYSTEM_PROMPT,
            input=f"Question: {question}\n\nContext:\n{context}\n\nRespond only in valid JSON.",
            max_output_tokens=2000,
            text={"format": {"type": "json_object"}},
        )
        raw = response.output_text.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Never let a parse error surface as an unhandled exception —
            # return a safe fallback that marks the response as unsupported.
            return {
                "answer": "Answer generation failed — response was not valid JSON.",
                "supported": False,
                "confidence": "low",
            }

    # ── Public interface ──────────────────────────────────────────────────────

    def ask(
            self,
            question: str,
            filters: dict | None = None,
            k: int = 5,
            retrieval_method: str = "hybrid_semantic",
    ) -> dict:
        """
        Full RAG pipeline: retrieve → generate → cite.
 
        Args:
            question         : natural language question
            filters          : optional OData filter dict (department, doc_type, year)
            k                : number of chunks to retrieve
            retrieval_method : "hybrid_semantic" | "hybrid" | "vector" | "keyword"
                               Overridden to "filtered_hybrid" when filters are provided.
 
        Returns:
            {
                "answer": str,
                "supported": bool,
                "confidence": "high" | "medium" | "low",
                "sources": list[dict],          # from retrieval only
                "retrieval_method": str,
                "chunks_retrieved": int,
                "latency_ms": float,
            }
        """
        t0 = time.perf_counter()

        # ── Step 1: Retrieve ──────────────────────────────────────────────────
        if filters:
            chunks = self.searcher.filtered_search(question, filters=filters, k=k)  
            retrieval_method ="filtered_hybrid"
        elif retrieval_method == "hybrid_semantic":
            chunks = self.searcher.hybrid_with_semantic(question, k=k)
        elif retrieval_method == "hybrid":
            chunks = self.searcher.hybrid_search(question, k=k)
        elif retrieval_method == "vector":
            chunks = self.searcher.vector_search(question, k=k)
        else:
            chunks = self.searcher.keyword_search(question, k=k)  

        # ── Short-circuit: nothing retrieved ─────────────────────────────────

        if not chunks:
            return {
                "answer": "This information is not available in the provided documents.",
                "supported": False,
                "confidence": "low",
                "sources": [],
                "retrieval_method": retrieval_method,
                "chunks_retrieved": 0,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            } 

        # ── Step 2: Build context string for LLM ─────────────────────────────
        context = self._build_context(chunks)  

        # ── Step 3: Generate answer + grounding decision ──────────────────────
        llm_output = self._generate(question, context)           

        supported = llm_output.get("supported", False)

        # ── Step 4: Build citations from retrieval only ───────────────────────
        # Sources are empty when not supported — listing retrieved chunks as
        # citations when they didn't answer the question would be misleading.
        sources = self._build_sources(chunks) if supported else []

        return {
            "answer": llm_output.get("answer", ""),
            "supported": supported,
            "confidence": llm_output.get("confidence", "low"),
            "sources": sources,
            "retrieval_method": retrieval_method,
            "chunks_retrieved": len(chunks),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }                            
            


