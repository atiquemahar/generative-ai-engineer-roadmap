# Day 13 — First Complete RAG Pipeline Findings

## Results
| Metric                        | Score |
|-------------------------------|-------|
| Source hit (correct category) | 20/20 |
| Grounded answer produced      | 19/20 |

## Pipeline Steps (Explicit — No Magic Chains)
1. `retrieve(query, k=3)` — FAISS similarity search against Day 12 index
2. `build_context(docs)` — numbered chunks with filename headers
3. Prompt construction — context + question passed to model
4. `client.responses.create()` — Azure OpenAI call (same pattern as Day 2)
5. Structured return — answer, sources, supported, chunks_used

## Source Hit Bug (Fixed)
Day 13 initial run showed 5/20 source hits.
Root cause: `check_source_hit()` compared the category string ("vendor_contracts")
against the filename ("VEN-CON-001.pdf") — never a match.

Fix applied: `SOURCE_CATEGORY_MAP` maps category names to filename prefixes.
Result after fix: 19/20 source hits.

## The One Miss — Q3: VPN Software
**Question:** "What VPN software is approved for remote access?"
**Answer:** "I don't have enough information in the provided documents to answer this question."
**Retrieved:** IT-PROC-002_Software_Installation.docx (x3)

This is a genuine content gap, not a retrieval failure. The document states that
personal VPN clients are *prohibited* but does not name an approved VPN solution.
The model correctly refused to fabricate an answer.

**Resolution options for later days:**
- Hybrid RAG (Day 18): keyword fallback may surface the prohibition context differently
- Agentic RAG: route to a different tool if no grounded answer found

## Answer Quality Observations

**Best answers (exact figures quoted):**
- Q1: "USD 25 — Receipts are required for all individual expenses above USD 25."
- Q5: Listed both contracts with different payment terms (21 days vs 30 days) — model
  synthesised across two retrieved chunks correctly
- Q8: Bullet-listed all three shortlisting criteria precisely

**Notable behaviour — Q5 (payment terms):**
Retrieved VEN-CON-003 and VEN-CON-001. Answer correctly distinguished:
  - Professional Services Agreement: 21 days
  - Cloud Hosting MSA: 30 days
This is multi-document synthesis working correctly.

**Notable behaviour — Q19 (data storage):**
Answer noted the sentence in the chunk was truncated ("The provided excerpt ends
with 'unless'"). Model flagged its own knowledge boundary — good grounding behaviour.

## Index Reuse
Loaded FAISS index from Day 12 — no re-embedding. Load time negligible vs 105s build time.
Results saved to: experiments/day13_rag_results.json (input for Day 14 citation analysis)

## What Day 14 Adds
- Structured `RAGResponse` with `Citation` objects (document, chunk_index, relevance_score)
- `is_grounded()` — deterministic heuristic (token overlap ratio, threshold 0.35)
- `answer_with_citations()` — never fabricates a source
- Not-found handling tested against 5 unanswerable questions