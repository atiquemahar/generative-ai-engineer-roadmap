"""
projects/knowledge_agent/retrieval/searcher.py
Day 18 — Hybrid Retrieval Comparison
 
Four search methods on the same Azure AI Search index:
  1. keyword_search       — BM25 only
  2. vector_search        — dense vector only
  3. hybrid_search        — BM25 + vector via RRF
  4. hybrid_with_semantic — hybrid + semantic reranker
 
UAE North supports semantic ranker on the free tier (verified July 2026).
Score note: BM25 @search.score is 1–7, RRF score is 0.01–0.03,
semantic @search.reranker_score is 0–4. Do not compare scores across methods.
"""
import os
import sys
import time
import csv
from pathlib import Path
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
 
load_dotenv(REPO_ROOT / ".env")

from projects.knowledge_agent.search.schema import (
    INDEX_NAME,
    SEMANTIC_CONFIG_NAME,
)

from projects.knowledge_agent.retrieval.hard_questions import GROUND_TRUTH

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
EMBEDDING_MODEL = os.environ["AZURE_EMBEDDING_DEPLOYMENT"]



SELECT_FIELDS = ["id", "content", "filename", "department", "heading", "doc_type"]

VALID_DEPARTMENTS = {
    "hr": "Human Resources",
    "human resources": "Human Resources",
    "it": "Information Technology",
    "information technology": "Information Technology",
    "finance": "Finance",
    "legal": "Legal",
}

# ─────────────────────────────────────────────────────────────────────────────
# HybridSearcher
# ─────────────────────────────────────────────────────────────────────────────

class HybridSearcher:
    def __init__(self,):
        self.openai_client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version="2025-04-01-preview",
        )
        self.search_client = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=INDEX_NAME,
            credential=AzureKeyCredential(SEARCH_API_KEY),
        )
        

    def _embed(self, query: str) -> list[float]:
        response = self.openai_client.embeddings.create(
            input=[query],
            model=EMBEDDING_MODEL, 
        )
        return response.data[0].embedding

    def _to_dicts(self, results) -> list[dict]:
        """Convert Azure search results to plain dicts — consistent return shape."""
        return [
            {field: r.get(field, "") for field in SELECT_FIELDS}
            | {"@search.score": r.get("@search.score", 0.0),
               "@search.reranker_score": r.get("@search.reranker_score")}
               for r in results
        ]
    def keyword_search(self, query: str, k: int = 1) -> list[dict]:
        """BM25 full-text search — no vectors, no reranking."""
        results = self.search_client.search(
            search_text=query,
            top=k,
            select=SELECT_FIELDS,
        )
        return self._to_dicts(results)

    def vector_search(self, query: str, k: int =1) -> list[dict]:
        """Pure vector search — cosine similarity against content_vector."""
        vector = self._embed(query)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=k,
            fields="content_vector",
        )
        results = self.search_client.search(
            search_text=None, # no keyword component
            vector_queries=[vector_query],
            top=k,
            select=SELECT_FIELDS,
        )
        return self._to_dicts(results)

    def hybrid_search(self, query: str, k: int =1) -> list[dict]:
        """
        Hybrid: BM25 + vector in a single request.
        Azure AI Search merges ranked lists via Reciprocal Rank Fusion (RRF).
        Adding search_text to vector_search is all that's needed.
        """
        vector = self._embed(query)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=k,
            fields="content_vector",
        )
        results = self.search_client.search(
            search_text=query, # BM25 component
            vector_queries=[vector_query],
            top=k,
            select=SELECT_FIELDS,
        )
        return self._to_dicts(results)

    def hybrid_with_semantic(self, query: str, k: int =1) -> list[dict]:
        """
        Hybrid + semantic reranker.
        Semantic reranker reads the top results from hybrid and reranks using
        Microsoft's cross-encoder model. Returns @search.reranker_score (0–4).
        UAE North supports semantic ranker on free tier — no tier upgrade needed.
        """
        vector = self._embed(query)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=50,
            fields="content_vector",
        )
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=k,
            select=SELECT_FIELDS,
            query_type="semantic",
            semantic_configuration_name=SEMANTIC_CONFIG_NAME,
        )
        return self._to_dicts(results)

    def build_filter_string(self, filters: dict) -> str | None: # day 19 
        """
        Build an OData filter string from a plain dict.

        Supported keys:
            department  : str  — "Finance", "Human Resources", "Information Technology", "Legal"
            doc_type    : str  — "pdf", "docx", "txt", "md"
            year        : int  — exact year match on effective_date
            year_from   : int  — effective_date >= year-01-01
            year_to     : int  — effective_date <= year-12-31

        Text filters are CASE-SENSITIVE and EXACT-MATCH in Azure AI Search.
        The values above must match what is stored in the index exactly.
        """
        if not filters:
            return None

        clauses = []

        if "department" in filters:
            # Normalise shorthand ("hr" → "Human Resources") so callers
            # don't need to remember the exact stored string.
            raw = filters["department"].strip()
            dept = VALID_DEPARTMENTS.get(raw.lower(), raw)
            dept = dept.replace("'", "''") # escape single quotes for OData
            clauses.append(f"department eq '{dept}'")

        if "doc_type" in filters:
            dt = filters["doc_type"].strip().lower().replace("'","''") 
            clauses.append(f"doc_type eq '{dt}'") 

        if "year" in filters:
            y = int(filters["year"])
            clauses.append(
                f"effective_date ge {y}-01-01T00:00:00Z "
                f"and effective_date lt {y + 1}-01-01T00:00:00Z"
            )
        else:
            if "year_from" in filters:
                y = int(filters["year_from"]) 
                clauses.append(f"effective_date ge {y}-01-01T00:00:00Z") 
            if "year_to" in filters:
                y = int(filters["year_to"]) 
                clauses.append(f"effective_date lt {y + 1}-01-01T00:00:00Z")

        return " and ".join(clauses) if clauses else None

    def filtered_search(  # day 19
            self, 
            query: str, 
            filters: dict | None = None,
            k: int =5,
            sort_by_date: bool = False) -> list[dict]:
        """
        Hybrid search with optional OData filter and optional date sort.

        Args:
            query       : natural language query
            filters     : dict passed to build_filter_string()
            k           : number of results to return
            sort_by_date: if True, sorts results by effective_date descending
                      (overrides relevance ranking — use only when recency matters)
        """ 
        filter_str = self.build_filter_string(filters) 
        vector = self._embed(query)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=k,
            fields="content_vector",
        )
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=k,
            select=SELECT_FIELDS,
            filter=filter_str,
            order_by=["effective_date desc"] if sort_by_date else None,
        )
        return self._to_dicts(results)


        




# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def run_evaluation(
        searcher: HybridSearcher, 
        method_name: str, 
        method_fn, 
        questions: list[tuple],
        k: int=1) -> list[dict]:
    rows = []
    for question, expected_file in questions:
        t0 = time.perf_counter()
        results = method_fn(question, k=k)
        latency_ms = (time.perf_counter() -t0) * 1000

        returned_files = [r.get("filename", "") for r in results]
        correct_found = int(expected_file in returned_files)
        irrelevant = sum(1 for f in returned_files if f !=expected_file)

        rows.append({
            "method": method_name,
            "question": question,
            "expected": expected_file,
            "correct_found": correct_found,
            "irrelevant_chunks": irrelevant,
            "latency_ms": round(latency_ms, 1),
        })
        time.sleep(0.3)  # avoid rate limits on embedding API

    return rows  

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    searcher = HybridSearcher()

    methods = [
        ("Keyword", searcher.keyword_search),
        ("Vector", searcher.vector_search),
        ("Hybrid", searcher.hybrid_search),
        ("Hybrid+Semantic", searcher.hybrid_with_semantic),
    ]

    all_rows = []
    for method_name, method_fn in methods:
        print(f"Running {method_name} ({len(GROUND_TRUTH)} questions)...")
        rows = run_evaluation(searcher, method_name, method_fn, GROUND_TRUTH)
        all_rows.extend(rows) 
        hits = sum(r["correct_found"] for r in rows)
        avg_latency = sum(r["latency_ms"] for r in rows) / len(rows)
        print(f"  → {hits}/{len(GROUND_TRUTH)} correct | {avg_latency:.0f}ms avg\n")

    # ── Save CSV ──────────────────────────────────────────────────────────────
    output_dir = Path(REPO_ROOT) / "evaluations"
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / "retrieval_comparison.csv"
 
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)
 
    print(f"Results saved to: {csv_path}") 

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  RETRIEVAL COMPARISON — 30 Questions, k=1")
    print(f"{'='*65}")
    print(f"  {'Method':<20} {'Correct':>8} {'Irrelevant':>11} {'Avg ms':>8}")
    print(f"  {'-'*20} {'-'*8} {'-'*11} {'-'*8}")
 
    for method_name, _ in methods:
        method_rows = [r for r in all_rows if r["method"] == method_name]
        correct    = sum(r["correct_found"]     for r in method_rows)
        irrelevant = sum(r["irrelevant_chunks"] for r in method_rows) / len(method_rows)
        avg_lat    = sum(r["latency_ms"]        for r in method_rows) / len(method_rows)
        pct        = correct / len(method_rows) * 100
        print(f"  {method_name:<20} {correct:>5}/{len(method_rows)} ({pct:>4.0f}%) "
              f"{irrelevant:>8.1f} {avg_lat:>8.0f}")
 
    print(f"\n  Correct  = expected file in top-{1} returned chunks")
    print(f"  Irrelevant = avg chunks per query NOT from expected file")
    print(f"  Latency includes embedding API call for vector/hybrid methods")
    print(f"\n  Note: @search.score is not comparable across methods.")
    print(f"  BM25 scores 1-7, RRF scores 0.01-0.03, semantic reranker 0-4.")   