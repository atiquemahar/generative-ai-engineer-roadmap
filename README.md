# Generative AI Engineer Roadmap

An 80-day hands-on build log toward enterprise GenAI engineering.
Every day produces working code, measured results, and documented findings.
No tutorials copied. No demos without numbers.


**Current progress: Day 22 of 80**

---

## What this is

A structured self-study project building real enterprise RAG systems on
Azure AI Foundry + Azure AI Search. The work is split into two phases:

**Phase 1 — Foundations (Days 1–15):** Local experiments with prompt engineering,
chunking strategies, retrieval methods, and citation pipelines. Each day
ends with an evaluation run and a findings document.

**Phase 2 — Production System (Days 16–21+):** A fully deployed enterprise
knowledge agent on Azure, built incrementally and evaluated against a
51-question benchmark.

---

## Stack

| Layer | Technology |
|-------|-----------|
| LLM & Embeddings | Azure OpenAI (GPT-4o, text-embedding-3-small) |
| Vector Search | Azure AI Search — HNSW + BM25 + Semantic Ranker |
| Document Loading | Docling (PDF, DOCX, MD, TXT) |
| API | FastAPI |
| Evaluation | Custom evaluation framework (Python) |
| Auth | Azure DefaultAzureCredential |

---

## Measured Results

### Phase 1 Highlights

**Day 3 — Prompt Engineering**

| Prompt Version | Pass Rate | Avg Latency |
|---|---:|---:|
| v1 Basic | 50% (10/20) | 5.05s |
| v2 Structured | 75% (15/20) | 4.45s |
| v3 Few-shot | 75% (15/20) | 4.72s |

**Day 11 — Chunking Strategy Comparison**

| Strategy | Chunks | Avg Size | Accuracy |
|---|---:|---:|---:|
| Fixed 500, no overlap | 95 | 382 chars | 8/9 |
| Fixed 500, overlap 100 | 100 | 396 chars | 8/9 |
| Small 200, overlap 50 | 268 | 141 chars | 8/9 |
| Heading-aware MD | 25 | 305 chars | 2/9 |

Selected: Fixed 500 no overlap — same accuracy at 3x lower embedding cost than small chunks.

**Day 12 — Semantic vs Keyword Search**

| Method | Score |
|---|---:|
| Keyword | 15/20 (75%) |
| Semantic | 20/20 (100%) |

Every keyword failure was vocabulary mismatch — the user's words and the document's
words were different strings for the same concept. Semantic embeddings resolved all 5.

**Day 15 — Retrieval Configuration**

| Configuration | Score |
|---|---:|
| Similarity k=3, 500 tokens | 25/30 |
| MMR k=5, 500 tokens | 28/30 |
| Similarity k=5, 1000 tokens | 29/30 |

Selected: Similarity k=5, max_output_tokens=1000. Proceeded to Phase 2.

---

### Phase 2 Highlights

**Day 18 — 4-Method Retrieval Benchmark (31 questions × 2 datasets × 2 k values)**

Baseline benchmark (document terminology):

| Method | Top-1 | Top-5 | Avg Latency |
|---|---:|---:|---:|
| Keyword | 94% | 97% | ~120ms |
| Vector | 100% | 100% | ~550ms |
| Hybrid | 100% | 100% | ~600ms |
| Hybrid + Semantic | 97% | 100% | ~1200ms |

Hard benchmark (paraphrased, natural language):

| Method | Top-1 | Top-5 |
|---|---:|---:|
| Keyword | **84%** | 94% |
| Vector | 100% | 100% |
| Hybrid | 100% | 100% |
| Hybrid + Semantic | 100% | 100% |

Key finding: Keyword search dropped 10 points under vocabulary mismatch.
Hybrid held at 100%. The semantic reranker produced one precision regression at k=1
on a structured tabular document — documented in `docs/day18_findings.md`.

**Day 20 — KnowledgeAgent: Structured Citations**

| Metric | Result |
|---|---:|
| Answerable correctly answered | 20/20 |
| Unanswerable correctly refused | 4/5 |
| Fabricated citations | 0 |

Citation safety is guaranteed by architecture: `_build_sources()` reads only from
retrieval output. The LLM never touches the source list.

**Day 21 — 51-Question Evaluation**

| Metric | Score | Target |
|---|---:|---:|
| Retrieval hit rate | 93% | > 70% ✓ |
| Direct questions | 100% | — |
| Multi-document questions | 80% | — |
| Ambiguous questions | 80% | — |
| Refusal accuracy | 90% | > 80% ✓ |
| Overall pass rate | 92% | — |

---

## Repository Structure

```
generative-ai-engineer-roadmap/
│
├── experiments/                      # Phase 1: daily experiments (Days 1–15)
│   ├── day01_first_call.py           # First Azure OpenAI API call
│   ├── day02_extractor.py            # Structured extraction with Pydantic
│   ├── day03_prompts_comparison.py   # Prompt version A/B/C comparison
│   ├── day09_local_rag.py            # Local RAG with FAISS
│   ├── day11_chunking.py             # Chunking strategy evaluation
│   ├── day12_vector_search.py        # Semantic vs keyword search
│   ├── day13_retrieval.py            # Retrieval pipeline
│   ├── day14_citations.py            # Citation integrity pipeline
│   ├── day15_mmr_retrieval.py        # MMR vs similarity comparison
│   └── prompts/                      # Prompt versions v1, v2, v3
│
├── projects/knowledge_agent/         # Phase 2: production RAG system
│   ├── ingestion/
│   │   └── pipeline.py               # Docling loader → Azure AI Search
│   ├── search/
│   │   ├── schema.py                 # Index schema: HNSW + semantic config
│   │   └── update_schema.py          # One-shot schema migration
│   ├── retrieval/
│   │   ├── searcher.py               # HybridSearcher: 4 methods + OData filters
│   │   ├── baseline_questions.py     # 31-question baseline benchmark
│   │   └── hard_questions.py         # 31-question paraphrased benchmark
│   ├── agent/
│   │   ├── knowledge_agent.py        # RAG pipeline: retrieve → generate → cite
│   │   ├── test_agent.py             # Citation verification: 25 questions
│   │   └── run_eval.py               # 51-question evaluation runner
│   ├── api/
│   │   ├── main.py                   # FastAPI application
│   │   └── routers/                  # /chat, /extract, /health endpoints
│   └── services/
│       └── extractor.py              # Structured complaint extraction
│
├── shared/
│   ├── ingestion/                    # Docling + document loaders
│   ├── evaluation/                   # Shared evaluation framework
│   └── models/                       # Pydantic models
│
├── data/enterprise_docs/             # 15 NovaTech enterprise documents
│   ├── hr_policies/                  # HR-POL-001/002/003 (PDF)
│   ├── leave_policies/               # HR-LEA-001/002/003 (MD)
│   ├── expense_guidelines/           # FIN-EXP-001/002/003 (TXT)
│   ├── it_procedures/                # IT-PROC-001/002/003 (DOCX)
│   └── vendor_contracts/             # VEN-CON-001/002/003 (PDF)
│
├── evaluations/                      # All evaluation outputs (CSV, JSON)
├── docs/                             # Findings documents per day
└── requirements.txt
```

---

## Azure AI Search Index

The production index (`enterprise-knowledge`) uses:

- **Vector field:** `content_vector` — 1536-dim embeddings (text-embedding-3-small)
- **HNSW algorithm:** configured via `hnsw-profile`
- **Semantic configuration:** `knowledge-semantic-config` with `content` as primary
  field and `heading`, `department` as keyword signals
- **Filterable fields:** `department`, `doc_type`, `effective_date`, `filename`
- **Duplicate detection:** MD5 chunk ID — safe to re-index without duplication

Retrieval methods available on `HybridSearcher`:

```python
searcher.keyword_search(query, k=5)          # BM25 only
searcher.vector_search(query, k=5)           # HNSW cosine similarity
searcher.hybrid_search(query, k=5)           # BM25 + vector via RRF
searcher.hybrid_with_semantic(query, k=5)    # Hybrid + cross-encoder reranker
searcher.filtered_search(query,              # Hybrid + OData filter
    filters={"department": "Finance",
             "year": 2026})
```

---

## Citation Safety

`KnowledgeAgent` guarantees zero source fabrication by design:

```
retrieve → [chunks: list[dict]] → _build_sources(chunks) → sources
                                        ↑
                               LLM never touches this
```

The LLM generates `answer`, `supported`, and `confidence` only.
`sources` is constructed by Python from the retrieval output.
This is not prompt engineering — it is architecture.

---

## Setup

**Requirements:** Python 3.11+, Azure subscription with Azure OpenAI and Azure AI Search.

```bash
git clone https://github.com/your-username/generative-ai-engineer-roadmap
cd generative-ai-engineer-roadmap
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

Create `.env` in the repo root:

```env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
MODEL_DEPLOYMENT_NAME=your-gpt4o-deployment
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your_search_key
```

**Index the documents (Day 17):**
```bash
python projects/knowledge_agent/search/update_schema.py
python projects/knowledge_agent/ingestion/pipeline.py
```

**Run the evaluation (Day 21):**
```bash
python projects/knowledge_agent/agent/run_eval.py
```

**Run the API:**
```bash
uvicorn projects.knowledge_agent.api.main:app --reload
```

---

## What's next (Days 22–80)

- Day 22: Groundedness judging (LLM-as-judge), 5-metric evaluation report
- Day 23–30: FastAPI endpoints, streaming responses, error handling
- Day 31–40: Azure AI Foundry deployment, monitoring
- Day 41–80: Multi-agent orchestration with LangGraph, CI/CD, enterprise hardening

---

## Findings documents

| Day | File | Topic |
|-----|------|-------|
| 3 | `experiments/day03_findings.md` | Prompt engineering comparison |
| 11 | `experiments/day11_findings.md` | Chunking strategy evaluation |
| 12 | `experiments/day12_findings.md` | Semantic vs keyword search |
| 14 | `experiments/day14_findings.md` | Citation pipeline design |
| 15 | `experiments/day15_findings.md` | MMR vs similarity retrieval |
| 18 | `docs/day18_findings.md` | Hybrid retrieval 4-method benchmark |

---

*Active build — updated daily.*