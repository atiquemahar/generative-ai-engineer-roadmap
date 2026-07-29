# Day 18 — Retrieval Benchmark Findings

## Objective

Evaluate four Azure AI Search retrieval strategies on the same enterprise knowledge base
across two benchmarks and two retrieval depths.

The benchmark compares:
- BM25 Keyword Search
- Vector Search (text-embedding-3-small)
- Hybrid Search (BM25 + Vector via RRF)
- Hybrid Search + Semantic Reranking (Microsoft cross-encoder)

---

## Evaluation Design

### Two Benchmarks

**Baseline benchmark** — 31 questions written using the same terminology as the source documents.

**Hard benchmark** — the same 31 questions rewritten using natural language, synonyms, and
conversational phrasing. Documents were never changed.

Examples of vocabulary substitutions in the hard benchmark:

| Document wording | Hard benchmark wording |
|------------------|------------------------|
| Annual Leave | Vacation / Paid Vacation |
| Dinner Per Diem | Spend on Dinner |
| Home Office Setup Allowance | Work From Home Equipment |
| Expense Claim | Travel Reimbursement |
| Notice Period | Leaving the Company |

### Two Retrieval Depths

- **k=1** — top-1 accuracy: does the correct chunk appear as the single returned result?
- **k=5** — top-5 accuracy: does the correct chunk appear anywhere in the five returned results?

k=1 is the condition that matters most in a RAG pipeline where only the top chunk is
passed to the LLM. k=5 measures recall.

---

## Results

### Top-1 Accuracy (k=1)

| Method | Baseline | Hard |
|--------|:--------:|:----:|
| Keyword | 29/31 (94%) | 26/31 (84%) |
| Vector | 31/31 (100%) | 31/31 (100%) |
| Hybrid | 31/31 (100%) | 31/31 (100%) |
| Hybrid + Semantic | **30/31 (97%)** | 31/31 (100%) |

### Top-5 Accuracy (k=5)

| Method | Baseline | Hard |
|--------|:--------:|:----:|
| Keyword | 30/31 (97%) | 29/31 (94%) |
| Vector | 31/31 (100%) | 31/31 (100%) |
| Hybrid | 31/31 (100%) | 31/31 (100%) |
| Hybrid + Semantic | 31/31 (100%) | 31/31 (100%) |

### Average Irrelevant Chunks in Top-5 (k=5)

| Method | Baseline | Hard |
|--------|:--------:|:----:|
| Keyword | 2.8 | 3.0 |
| Vector | 1.5 | 1.3 |
| Hybrid | 1.6 | 1.4 |
| Hybrid + Semantic | 1.9 | 1.8 |

Note: the Hybrid+Semantic irrelevant count being slightly higher than Hybrid is discussed
under Finding 4. It reflects a limitation of file-level ground truth labels, not
a straightforward retrieval failure.

### Average Latency

Latency includes the embedding API call for all vector-based methods.
Individual run figures have variance due to network conditions — the structural
gap between keyword and embedding-based methods is the reliable signal.

| Method | Baseline k=1 | Baseline k=5 | Hard k=1 | Hard k=5 |
|--------|:------------:|:------------:|:--------:|:--------:|
| Keyword | 470ms | 589ms | 114ms | 84ms |
| Vector | 1538ms | 571ms | 1621ms | 697ms |
| Hybrid | 577ms | 627ms | 1217ms | 518ms |
| Hybrid + Semantic | 602ms | 1232ms | 792ms | 537ms |

Keyword latency does not include embedding API calls and sits in the 80–120ms range
under stable conditions. Embedding-based methods add 400–1200ms depending on API
response time. The high variance in individual runs makes precise latency comparisons
unreliable; the structural difference is what matters for architecture decisions.

---

## Key Findings

### 1. Keyword retrieval is sensitive to vocabulary mismatch

BM25 Top-1 accuracy dropped from 94% on the baseline to 84% on the hard benchmark — a
10-point drop caused entirely by vocabulary substitution. The documents did not change.
The same information was simply asked about using different words.

Representative failures:

| Hard query | Expected document term |
|------------|------------------------|
| "How much paid vacation after three years?" | Annual Leave |
| "What can I spend on dinner during a business trip?" | Per Diem Allowance |
| "Does the company help with work from home equipment?" | Home Office Setup Allowance |

BM25 matches on token overlap. When query tokens don't appear in the document,
the relevant chunk scores low or is absent entirely.

### 2. Embedding-based retrieval is robust to paraphrasing

Vector Search achieved 100% Top-1 accuracy on both benchmarks without any tuning.
The embedding space captures semantic similarity regardless of surface-level wording,
which is why "paid vacation" and "annual leave" resolve to nearby vectors.

This is the primary argument for vector search in enterprise RAG where users ask
questions in their own words rather than using policy document terminology.

### 3. Hybrid search matches vector accuracy while adding lexical precision

Hybrid Search matched Vector Search at 100% across both benchmarks and both k values.
The RRF merger preserved the vector search's vocabulary-mismatch robustness while
adding BM25's exact-match strength for queries where terminology does overlap.

For this corpus, Hybrid is strictly better than or equal to Keyword on every metric.
There is no scenario in these results where adding the keyword component hurt.

### 4. Semantic reranking produced a precision regression at k=1 on the baseline

Hybrid+Semantic dropped to 30/31 (97%) on the baseline k=1 run while plain Hybrid
achieved 31/31. The affected question:

> "How many days annual leave does an employee with 3 years service get?"
> Expected: HR-LEA-001_Annual_Leave_Policy.md

The same question rephrased for the hard benchmark:

> "After working here for three years, how much paid vacation do I receive each year?"
> Result: 1/1 correct

The semantic reranker demoted the correct chunk on formal document vocabulary and
promoted it on conversational phrasing. This reveals how the cross-encoder works:
it scores query-chunk pairs on natural language Q&A alignment, not keyword overlap.

The entitlement table in HR-LEA-001 (structured rows of "0–2 years → 20 days") reads
as a weaker answer to a formal policy question than prose chunks that *discuss* annual
leave. The same table reads as a direct answer to the conversational first-person query.

This is a documented limitation: semantic rerankers are trained on prose Q&A pairs
and can misrank structured tabular content, which is common in enterprise HR and
finance documents.

**Production implication:** at k=1, adding a semantic reranker to an already-accurate
hybrid retriever can introduce precision regressions on formal or structured queries.
The reranker provides the most value when the initial hybrid ranking is genuinely
ambiguous — for example, when multiple chunks from different documents are plausible
answers. On this corpus, hybrid search rarely produced ambiguous rankings, so the
reranker had limited opportunity to improve and occasional opportunity to regress.

### 5. Irrelevant chunk count is higher for Hybrid+Semantic at k=5

Hybrid+Semantic consistently returns slightly more chunks from non-expected files than
plain Hybrid. This is partially a ground-truth labelling artefact: the reranker may
promote a chunk from a different file that genuinely answers the question (for example,
a Finance policy chunk that also mentions annual leave approval), which the evaluation
counts as irrelevant because it doesn't match the single expected file.

It also reflects the reranker's broader candidate pool (k_nearest_neighbors=50 for the
vector side) which surfaces more cross-document candidates before trimming to top-5.

---

## Conclusion

For this enterprise knowledge base:

**Keyword Search** is fast (sub-150ms) but degrades meaningfully under vocabulary
mismatch. It is suitable only when user queries are expected to mirror document
terminology.

**Vector Search** is robust to paraphrasing and achieved perfect accuracy across both
benchmarks, at the cost of embedding API latency (~500–1600ms per query).

**Hybrid Search** matched Vector Search on every accuracy metric while adding BM25
precision for exact-match queries. It is the recommended default for this corpus.

**Hybrid + Semantic Reranking** did not improve Top-5 accuracy on this dataset, and
produced one precision regression at k=1 on a structured tabular document. The reranker
provides the most value when hybrid candidates are genuinely ambiguous, or when the
downstream use case requires Q&A captions and semantic answers for display in a UI.
Its latency overhead (roughly 2x hybrid at k=5) is only justified when ranking quality
demonstrably matters.

The retrieval benchmark establishes a quantitative baseline for subsequent RAG
evaluations covering groundedness, citation accuracy, and answer quality in the
complete pipeline.

---

## Files

- `projects/knowledge_agent/retrieval/searcher.py` — HybridSearcher class, four methods
- `projects/knowledge_agent/retrieval/hard_questions.py` — hard benchmark ground truth
- `projects/knowledge_agent/search/schema.py` — index schema with semantic configuration
- `projects/knowledge_agent/search/update_schema.py` — one-shot schema update script
- `evaluations/retrieval_comparison.csv` — raw per-question results across all runs