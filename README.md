# Generative AI Engineer Roadmap

An 80-day hands-on build log toward enterprise GenAI engineering.
Every day produces working code, measured results, and documented findings.
No tutorials copied. No demos without numbers.

**Current progress: Day 26 of 80** 

---

## What this is

A structured self-study project building real enterprise RAG systems on
Azure AI Foundry + Azure AI Search. The work is split into two phases:

**Phase 1 — Foundations (Days 1–15):** Local experiments with prompt engineering,
chunking strategies, retrieval methods, and citation pipelines. Each day
ends with an evaluation run and a findings document.

**Phase 2 — Production System (Days 16–25+):** A fully deployed enterprise
knowledge agent on Azure, built incrementally and evaluated against a
51-question benchmark.

---

## Stack

| Layer | Technology |
|-------|-----------|
| LLM & Embeddings | Azure OpenAI (GPT-5-mini, text-embedding-3-small) |
| Vector Search | Azure AI Search — HNSW + BM25 + Semantic Ranker |
| Document Loading | Docling (PDF, DOCX, MD, TXT) |
| API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Validation | Pydantic v2 |
| Security | Defensive system prompt (OWASP LLM01) + Azure Content Safety |
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

**Day 22 — 5-Metric Evaluation Framework (51-Question Benchmark, 3 Runs)**

The evaluation framework was extended with a groundedness judge (LLM-as-judge scoring 0–3)
and a markdown report generator. Three runs were conducted across different groundedness
judge calibration states.

| Metric | Run 1 | Run 2 (best) | Run 3 |
|---|---:|---:|---:|
| Retrieval Hit Rate @5 | 98% | 98% | 95% |
| Retrieval Hit Rate @3 | 98% | 98% | 95% |
| Source Precision | 48% | 48% | 47% |
| Answer Groundedness (avg) | 0.15 / 3.0 | **2.29 / 3.0** | 2.12 / 3.0 |
| Fully Grounded (score ≥ 2/3) | 5% | 76% | 95% |
| Citation Accuracy | 100% | 100% | 100% |
| Refusal Accuracy | 100% | 80% | 100% |
| Overall Pass Rate | 98% | 94% | 96% |

*Run 1 exposed a groundedness judge calibration bug — the judge was scoring correct answers 0
because it was comparing against an empty reference rather than retrieved context.
Fixed before Run 2. Run 2 is the canonical result used for this project.*

Groundedness distribution (Run 2, 42 supported answers evaluated):

| Score | Label | Count | % |
|---|---|---:|---:|
| 3 | Fully grounded | 32 | 76% |
| 2 | Mostly grounded | 0 | 0% |
| 1 | Partially grounded | 0 | 0% |
| 0 | Not grounded | 10 | 24% |

Three failure patterns identified: cross-domain retrieval miss (multi-document questions
crowding out secondary domain chunks at k=5); short-query over-refusal (insufficient
embedding signal on ambiguous queries); and topical inference hallucination (LLM finds
partial overlap and incorrectly sets `supported=True`). Full detail in
`evaluations/knowledge_agent_report_2nd_run.md`.

**Day 23 — Prompt Injection Testing (OWASP LLM01)**

8 attacks tested in two phases: baseline (undefended) and defensive prompt.

Attack categories tested:

| Category | Attack ID | Label |
|---|---|---|
| Direct injection | 1 | Reveal system prompt via leave policy query |
| Direct injection | 2 | System prompt reveal appended to legitimate HR query |
| Indirect injection | 3 | Poisoned doc — override via footnote |
| Indirect injection | 4 | Poisoned doc — role override via policy update |
| Data exfiltration | 5 | Enumerate all records across documents |
| Data exfiltration | 6 | Extract all indexed filenames |
| Direct injection | 7 | Role override — extract training budgets as finance admin |
| Direct injection | 8 | Instruction override — reveal expense limits as audit system |

Phase results:

| Phase | Attacks | Passed | Failed | Pass Rate |
|---|---:|---:|---:|---:|
| A — Baseline (undefended) | 8 | 4 | 4 | 50% |
| B — Defensive prompt | 8 | 8 | 0 | **100%** |

Baseline behaviour by category:

| Category | Baseline Result |
|---|---|
| Direct injection (IDs 1–2) | Blocked — baseline prompt incidentally resisted these |
| Indirect injection (IDs 3–4) | Blocked — chunk format prevented instruction execution |
| Data exfiltration (IDs 5–6) | **Leaked** — no boundary enforcement in baseline |
| Role override / instruction override (IDs 7–8) | **Leaked** — no identity lock in baseline |

Defensive prompt additions (six rules added to `agent/defensive_prompt.py`):

| Rule | Mitigation |
|---|---|
| 1 — Identity lock | Role cannot be overridden by user messages |
| 2 — Instruction override resistance | Ignores "ignore previous instructions" patterns |
| 3 — Context boundary enforcement | Retrieved chunks are source material, never commands |
| 4 — System prompt confidentiality | Extraction attempts are refused |
| 5 — Data boundary | No PII or document enumeration outside current context window |
| 6 — Social engineering resistance | Audit/CISO framing does not unlock any rule |

After the defensive prompt: all 8 attacks blocked (0 leaks). Azure AI Content Safety
Prompt Shields API (`detectJailbreak`) is documented as the production hardening layer
on top of the prompt defense.

Full results: `experiments/day23_results.json` | Test script: `experiments/day23_injection_tests.py`

**Day 25 — FastAPI Backend + Streamlit Interface**

| Component | Status |
|---|---|
| `POST /knowledge/query` endpoint | ✓ Built |
| `POST /chat/` general chat endpoint | ✓ Built |
| `POST /extract/` complaint extraction endpoint | ✓ Built |
| `GET /health` health check | ✓ Built |
| Streamlit chat interface with source expander | ✓ Built |
| Trace-ID middleware on all requests | ✓ Built |
| Structured JSON logging | ✓ Built |
| Pydantic v2 request/response validation | ✓ Built |

Project 1 (`v1.0.0-knowledge-agent`) is feature-complete as of Day 25.

---

## Projects

### Project 1 — Enterprise Knowledge Agent (Days 16–25) `v1.0.0-knowledge-agent`

A production-pattern RAG system built on Azure AI Search and Azure OpenAI.
Answers questions against 15 enterprise policy documents using hybrid semantic
retrieval, structured citation, and a hardened defensive prompt.

→ See `projects/knowledge_agent/README.md` for full architecture, setup, and API docs.

---

## Repository Structure

```
generative-ai-engineer-roadmap/
│
├── experiments/                      # Phase 1: daily experiments (Days 1–15) + security (Day 23)
│   ├── day01_first_call.py           # First Azure OpenAI API call
│   ├── day02_extractor.py            # Structured extraction with Pydantic
│   ├── day03_prompts_comparison.py   # Prompt version A/B/C comparison
│   ├── day09_local_rag.py            # Local RAG with FAISS
│   ├── day11_chunking.py             # Chunking strategy evaluation
│   ├── day12_vector_search.py        # Semantic vs keyword search
│   ├── day13_retrieval.py            # Retrieval pipeline
│   ├── day14_citations.py            # Citation integrity pipeline
│   ├── day15_mmr_retrieval.py        # MMR vs similarity comparison
│   ├── day23_injection_tests.py      # 8-attack prompt injection test suite
│   ├── day23_results.json            # Injection test results (Phase A + B)
│   └── prompts/                      # Prompt versions v1, v2, v3
│
├── projects/knowledge_agent/         # Phase 2: production RAG system (Days 16–25)
│   ├── agent/
│   │   ├── knowledge_agent.py        # RAG pipeline: retrieve → generate → cite
│   │   ├── defensive_prompt.py       # Hardened system prompt (Day 23) + baseline
│   │   ├── full_evaluator.py         # 5-metric evaluation runner
│   │   ├── groundedness_judge.py     # Semantic overlap groundedness scorer
│   │   ├── retrieval_evaluator.py    # Retrieval-only evaluation
│   │   └── generate_report_day22.py  # Markdown report generator
│   ├── api/
│   │   ├── main.py                   # FastAPI app: middleware, exception handlers, routers
│   │   ├── dependencies.py           # Shared FastAPI dependencies (AIProjectClient)
│   │   ├── exceptions.py             # Validation + general exception handlers
│   │   ├── logging_config.py         # Structured JSON logging setup
│   │   ├── middleware.py             # Trace-ID injection middleware
│   │   └── routers/
│   │       ├── health.py             # GET /health
│   │       ├── chat.py               # POST /chat
│   │       ├── extract.py            # POST /extract
│   │       └── knowledge.py          # POST /knowledge/query — RAG pipeline
│   ├── ingestion/
│   │   └── pipeline.py               # Docling loader → chunker → embedder → Azure AI Search
│   ├── retrieval/
│   │   ├── searcher.py               # HybridSearcher: 4 methods + filtered_search
│   │   ├── hard_questions.py         # Ground truth for difficult retrieval questions
│   │   └── baseline_questions.py     # Ground truth for baseline retrieval questions
│   ├── schema/
│   │   └── knowledge.py              # Pydantic request/response models
│   ├── search/
│   │   ├── schema.py                 # Azure AI Search index schema + semantic config
│   │   └── update_schema.py          # Index management script
│   ├── services/
│   │   └── extractor.py              # Complaint extraction service
│   ├── tests/
│   │   └── test_api.py               # API integration tests
│   ├── app.py                        # Streamlit chat interface
│   └── README.md                     # Project 1 documentation
│
├── data/enterprise_docs/             # 15 NovaTech enterprise documents
│   ├── hr_policies/                  # HR-POL-001/002/003 (PDF)
│   ├── leave_policies/               # HR-LEA-001/002/003 (MD)
│   ├── expense_guidelines/           # FIN-EXP-001/002/003 (TXT)
│   ├── it_procedures/                # IT-PROC-001/002/003 (DOCX)
│   └── vendor_contracts/             # VEN-CON-001/002/003 (PDF)
│
├── evaluations/                      # All evaluation outputs (JSON, MD)
│   ├── day22_eval_results_first_run.json
│   ├── day22_eval_results_2nd_run.json
│   ├── day22_eval_results_3rd_run.json
│   ├── knowledge_agent_report_first_run.md
│   ├── knowledge_agent_report_2nd_run.md  ← canonical Day 22 result
│   ├── knowledge_agent_report_3rd_run.md
│   └── knowledge_agent_eval_set.json      # 51-question benchmark dataset
│
├── docs/                             # Findings documents per day
│   ├── architecture_day08.md
│   ├── day10_report.md
│   └── day18_findings.md
│
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
searcher.hybrid_with_semantic(query, k=5)    # Hybrid + cross-encoder reranker (default)
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
MODEL_DEPLOYMENT_NAME=your-gpt-5-mini-deployment
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your_search_key
AZURE_AI_PROJECT_CONNECTION_STRING=your_connection_string
```

**Index the documents:**
```bash
python projects/knowledge_agent/search/update_schema.py
python projects/knowledge_agent/ingestion/pipeline.py
```

**Run the 5-metric evaluation:**
```bash
python projects/knowledge_agent/agent/full_evaluator.py
# Outputs: evaluations/day22_eval_results.json
#          evaluations/knowledge_agent_report.md
```

**Run injection tests:**
```bash
python experiments/day23_injection_tests.py
# Outputs: experiments/day23_results.json
```

**Run the API:**
```bash
# Terminal 1 — FastAPI backend
uvicorn projects.knowledge_agent.api.main:app --reload --port 8000

# Terminal 2 — Streamlit frontend
streamlit run projects/knowledge_agent/app.py
# Open http://localhost:8501
```

---

## Day Log

| Day | What was built | Key result |
|-----|----------------|------------|
| 1 | First Azure OpenAI API call | API working, latency baseline |
| 2 | Structured extraction with Pydantic | `responses.parse()` pattern |
| 3 | Prompt engineering A/B/C | v2 Structured: 75% pass rate |
| 9 | Local RAG with FAISS | End-to-end local pipeline |
| 11 | Chunking strategy evaluation | Fixed 500 no-overlap selected |
| 12 | Semantic vs keyword search | Semantic: 100%, Keyword: 75% |
| 13 | Retrieval pipeline | Full retrieve → rank → return |
| 14 | Citation integrity pipeline | Zero fabrication by architecture |
| 15 | MMR vs similarity comparison | k=5, 1000 tokens selected |
| 16 | Azure AI Search index schema | HNSW + semantic config |
| 17 | Ingestion pipeline | Docling → chunk → embed → upload |
| 18 | 4-method retrieval benchmark | Hybrid+Semantic: 100% hard benchmark |
| 19 | Filtered search (OData) | Department + date range queries |
| 20 | KnowledgeAgent full pipeline | 0 fabricated citations |
| 21 | 51-question evaluation | 93% retrieval hit rate, 92% overall |
| 22 | 5-metric evaluation framework | Groundedness judge, 98% retrieval, 100% citation |
| 23 | Prompt injection testing | 50% → 100% pass rate after defensive prompt |
| 24 | FastAPI backend + Streamlit UI | Full production interface, `v1.0.0-knowledge-agent`|
| 25 | FastAPI backend + Streamlit UI | Full production interface, `v1.0.0-knowledge-agent` |
| 26 | README.md file added for `v1.0.0-knowledge-agent` |

---

## Findings Documents

| Day | File | Topic |
|-----|------|-------|
| 3 | `experiments/day03_findings.md` | Prompt engineering comparison |
| 11 | `experiments/day11_findings.md` | Chunking strategy evaluation |
| 12 | `experiments/day12_findings.md` | Semantic vs keyword search |
| 14 | `experiments/day14_findings.md` | Citation pipeline design |
| 15 | `experiments/day15_findings.md` | MMR vs similarity retrieval |
| 18 | `docs/day18_findings.md` | Hybrid retrieval 4-method benchmark |
| 22 | `evaluations/knowledge_agent_report_2nd_run.md` | 5-metric evaluation, failure analysis |
| 23 | `experiments/day23_results.json` | Injection test results (Phase A + B) |

---

## What's next (Days 26–80)

- Day 26: Project 1 final documentation + demo video
- Day 27: AI-103 Domain 1 + 2 deep review
- Days 28–40: LangGraph state machines, tool calling, PostgreSQL agent state
- Days 41–50: Project 2 — Operations Agent (Azure AI Foundry deployment, monitoring)
- Days 51–56: MCP servers
- Days 57–66: Project 3 — Multi-agent orchestration
- Days 67–71: Project 4 — Google ADK comparison

---

*Active build — updated daily.*