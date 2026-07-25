# Day 15 — Retrieval Evaluation Findings

## Final Configuration (Proceeding to Day 16)

```
Retrieval:        Similarity search
k:                5
max_output_tokens: 1000
Overall pass rate: 29/30 (96.7%)
```

---

## Complete Run History

| Run | Retrieval | k | Tokens | Score | Primary issue |
|---|---|---:|---:|---:|---|
| Day 14 baseline | Similarity | 3 | 500 | 4/30 | Evaluation metadata bug (source path vs filename) |
| Run 2 | Similarity | 3 | 500 | 20/30 | Source-category prefix fix applied |
| Run 3 | Similarity | 3 | 500 | 25/30 | Citation/retrieval separation fixed; probation case corrected |
| Day 15 MMR | MMR | 5 | 500 | 28/30 (93.3%) | 2 failures: false refusal + incomplete answer |
| Day 15 Similarity | Similarity | 5 | 1000 | 29/30 (96.7%) | 1 failure: policy ambiguity at exactly 3 years |

---

## Final Comparison: MMR vs Similarity

Both configurations reach near-identical scores on the current 30-case suite.

| Configuration | Score | Remaining failure |
|---|---:|---|
| MMR, k=5, fetch_k=20, 500 tokens | 28/30 | False refusal on onboarding question (answer exists in doc) |
| Similarity, k=5, 1000 tokens | 29/30 | Sick-leave ambiguity at exactly 3 years (data issue, not retrieval) |

**Decision: proceed with similarity search, k=5, max_output_tokens=1000.**

MMR still failed a genuinely answerable question despite the exact answer existing
in the retrieved document. The similarity-search failure is a test-data ambiguity,
not a retrieval or generation problem. Similarity search is the stronger baseline
for the Phase 3 project.

MMR latency was lower in this run (3,656 ms vs 4,922 ms) but a single run is not
sufficient evidence that MMR is consistently faster — LLM generation latency varies.

---

## The One Remaining Failure — Sick Leave at 3 Years

**Question:** "What is the sick leave entitlement for 3 years experience?"
**Expected keyword:** `15`
**Retrieved:** HR-LEA-002_Sick_Leave_Policy.md ✓
**Result:** Model refused or gave ambiguous answer

**Root cause — policy table has an overlapping boundary:**

```
1–3 years  → 15 days
3+ years   → 20 days
```

At exactly 3 years both rows appear to apply. The model correctly identifies the
ambiguity. This is a test-data problem, not a retrieval or generation failure.

**Fix for Day 16 onward — replace with unambiguous question:**

```json
{
  "question": "What is the sick leave entitlement for 2 years of service?",
  "expected_source": "leave_policies",
  "expected_supported": true,
  "expected_keywords": ["15"]
}
```

or:

```json
{
  "question": "What is the sick leave entitlement for 4 years of service?",
  "expected_source": "leave_policies",
  "expected_supported": true,
  "expected_keywords": ["20"]
}
```

---

## Experiment Design — What Each Run Isolated

The four Day 15 runs were not perfectly controlled comparisons because retrieval
strategy and output-token budget changed together. The correct isolated comparison
is:

| Run | Retrieval | k | Tokens | What it isolates |
|---|---|---:|---:|---|
| Day 14 baseline | Similarity | 3 | 500 | Original baseline |
| Day 15 MMR | MMR | 5 | 500 | Diversity vs similarity (equal token budget) |
| *(not run)* | Similarity | 5 | 500 | k=3 vs k=5 with same strategy and tokens |
| Day 15 final | Similarity | 5 | 1000 | Output budget effect on completeness |

The `similarity k=5, tokens=500` run was not executed. The 29/30 result therefore
combines the effect of larger k and larger output budget — both likely contributed.
The annual-leave incomplete answer from MMR run (truncated at 500 tokens) resolved
at 1000 tokens, suggesting the output budget was the primary factor there.

**Implication for Day 16+:** if the Phase 3 project shows incomplete answers,
increase `max_output_tokens` before changing retrieval strategy.

---

## Evaluation Fixes Applied Across Runs

### Run 1 → Run 2: Source-category prefix map

```python
SOURCE_CATEGORY_MAP = {
    "expense_guidelines": ["fin-exp"],
    "leave_policies":     ["hr-lea"],
    "hr_policies":        ["hr-pol"],
    "it_procedures":      ["it-proc"],
    "vendor_contracts":   ["ven-con"],
}
```

Filenames like `VEN-CON-001_CloudHosting_MSA.pdf` do not contain the string
`"vendor_contracts"`. Without this map, all vendor contract retrieval checks
returned False regardless of what was actually retrieved.

### Run 2 → Run 3: Retrieval evidence separated from citations

```python
retrieved_sources: list[str] = Field(default_factory=list)  # raw FAISS results
citations: list[Citation] = []                               # only for supported answers
```

Refusals correctly return empty citations. The evaluator now measures retrieval
against `retrieved_sources`, not `citations`, so refusals are not penalised for
having no citations.

### Run 3 → Run 4: Probation policy corrected

```json
{
  "question": "What is the probation period policy at NovaTech?",
  "expected_supported": false
}
```

No probation content exists in any of the 15 source documents. This was always
an unanswerable question — the test case was misconfigured.

---

## MMR Limitation to Document

`max_marginal_relevance_search()` does not return FAISS similarity scores.
All citation relevance scores from the MMR run display as `0.000`.
These are placeholders, not MMR scores, and should not be used to compare
chunk quality. This is documented so the Day 16 evaluation report is not
misread.

---

## Saved Files

| File | Contents |
|---|---|
| `evaluations/rag_baseline.json` | Day 14 / Run 1 raw results |
| `evaluations/day15_mmr_results.json` | Day 15 MMR run (28/30) |
| `evaluations/day15_similarity_k5_tokens1000.json` | Day 15 final run (29/30) |

Do not overwrite `rag_baseline.json` — it is the Day 14 reference point for
all future comparisons in Phase 3.

---

## Metrics at Final Configuration (29/30)

| Metric | Score |
|---|---:|
| Total test cases | 30 |
| Answerable questions | 23 |
| Unanswerable questions | 7 |
| Retrieval hit rate | 100% (23/23) |
| Groundedness rate | 95.7% (22/23) |
| Keyword accuracy | 91.3% (21/23) |
| Refusal accuracy | 100% (7/7) |
| Overall pass rate | 96.7% (29/30) |
| Average latency | 4,922 ms |

---

## Proceeding to Day 16

Phase 3 (Enterprise Knowledge Agent, Days 16–27) starts with this baseline:

- Retrieval: similarity search, k=5
- Embeddings: text-embedding-3-small
- Output budget: max_output_tokens=1000
- Pass rate: 96.7%
- Known open issue: sick-leave boundary ambiguity (test data fix, not code fix)
