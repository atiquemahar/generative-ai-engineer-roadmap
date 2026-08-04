# Knowledge Agent Evaluation Report

**Generated:** 2026-08-03T08:09:57.903002+00:00Z
**Dataset:** knowledge_agent_eval_set.json (51 questions)
**Retrieval method:** hybrid_semantic (k=5)

---

## Summary Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Retrieval Hit Rate @5 | 98% | > 70% |
| Retrieval Hit Rate @3 | 98% | — |
| Source Precision | 48% | — |
| Answer Groundedness (avg) | 0.15 / 3.0 | — |
| Answer Grounded (≥ 2/3) | 5% | — |
| Citation Accuracy | 100% | 100% |
| Refusal Accuracy | 100% | > 80% |
| Overall Pass Rate | 98% | — |

---

## Category Breakdown

| Category | Count | Retrieval Hit @5 |
|----------|-------|-----------------|
| Direct | 26 | 100% |
| Multi-Document | 10 | 100% |
| Ambiguous | 5 | 80% |
| Unanswerable | 10 | Refusal: 100% |

---

## Answer Groundedness Distribution

Evaluated on 40 supported answers.

| Score | Label | Count | % |
|-------|-------|-------|---|
| 3 | Fully grounded | 2 | 5% |
| 2 | Mostly grounded | 0 | 0% |
| 1 | Partially grounded | 0 | 0% |
| 0 | Not grounded | 38 | 95% |

---

## Citation Accuracy

Citation accuracy is 100% by architectural design. The `_build_sources()` method
constructs the citation list directly from the list returned by `HybridSearcher`.
The LLM is never asked to generate source references — it produces answer text only.
This design makes source fabrication structurally impossible regardless of prompt.

---

## Top 3 Failure Patterns

### Pattern 1 — Cross-domain retrieval miss

**Affected questions:** multi_document category

When a question spans two departments (e.g. HR + IT, or two vendor contracts),
the less semantically obvious document gets crowded out of the top-5 by
same-domain content. The embedding vector skews toward the more prominent domain
and the secondary document never scores high enough to be retrieved.

**Root cause:** k=5 is insufficient when both expected sources need to rank in the
top half of results for different sub-domains. No prompt change can fix a retrieval miss.

**Potential fix:** increase k to 8 for multi-part queries, or apply a department
filter to force coverage of each required domain in separate retrieval passes.

### Pattern 2 — Short/ambiguous query over-refusal

Short, ambiguous questions do not give the embedding model enough signal.
The retrieved chunks may contain the relevant policy section but the LLM
evaluates each chunk as not fully answering the question and refuses.

**Root cause:** very short queries produce low-precision embeddings that
retrieve broadly relevant but not pinpoint-accurate chunks. The grounding
guardrail then correctly rejects an answer that would require inference,
but the context actually does contain the answer in a specific subsection.

**Potential fix:** query expansion — rewrite short queries before embedding
to add context clues, or use a dedicated 'question type' classifier to
route ambiguous questions to a broader context window.

**Affected questions:**

- [38] Can I work while on leave?
  - Retrieval: 5 chunks retrieved, supported=False

### Pattern 3 — Topical inference hallucination

The LLM sets `supported=True` for a question that is technically unanswerable
because retrieved chunks are topically related but do not explicitly state
the requested policy. The 'explicitly state' guardrail in the system prompt
catches most cases but fails when the semantic overlap is genuine.

**Root cause:** the corpus contains partial policy coverage that overlaps
with out-of-scope topics. For example, remote work arrangements partially
resemble flexible hours. The LLM finds a plausible answer and misidentifies
it as explicitly stated.

**Potential fix:** add a validation step that confirms the answer text
contains explicit policy language (numbers, named sections, dates) rather
than general statements. Unanswerable questions tend to produce vaguer answers.

---

## Failed Questions Detail

### [38] [ambiguous]

**Question:** Can I work while on leave?
**Expected sources:** ['HR-LEA-003_Parental_Leave_Policy.md']
**Returned sources:** []
**Expected supported:** True
**Actual supported:** False (confidence: high)
**Answer:** This information is not available in the provided documents.

---

## Recommendations

1. **Increase k for multi-part queries.** Set k=8 when the query contains
   conjunctions ('and', 'both', 'as well as') or explicitly spans multiple topics.

2. **Query expansion for short queries.** Queries under 8 words should be
   expanded before embedding to improve retrieval precision.

3. **Secondary groundedness check for unanswerable detection.** Before
   returning supported=True, verify the answer contains at least one explicit
   policy marker (a number, date, named section, or specific dollar amount).
   Answers without these markers on policy questions are likely inferences.
