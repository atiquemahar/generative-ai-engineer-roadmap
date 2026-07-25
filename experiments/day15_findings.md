# Day 15 — MMR Retrieval Findings

## Final Results

| Metric | Score |
|---|---:|
| Total test cases | 30 |
| Answerable questions | 23 |
| Unanswerable questions | 7 |
| Retrieval hit rate | 100% (23/23) |
| Groundedness rate | 95.7% (22/23) |
| Keyword accuracy | 91.3% (21/23) |
| Refusal accuracy | 100% (7/7) |
| Overall pass rate | 93.3% (28/30) |
| Average latency | 3,808 ms |

---

## Run History

The project reached the Day 15 result through four iterations. The early runs are useful because they show the difference between a retrieval problem, an evaluation-metadata problem, and an answer-generation problem.

| Run | Result | What changed or was discovered |
|---|---:|---|
| Run 1 | 4/30 passes | The first baseline evaluation exposed a source-tracking problem. The evaluator looked only at citations, while refusals intentionally had no citations. In addition, some FAISS metadata used `source` paths rather than `filename`, so source-category checks could not reliably identify retrieved documents. |
| Run 2 | 20/30 passes | Source normalization and category-prefix checks were introduced. Source names such as `FIN-EXP`, `HR-LEA`, `HR-POL`, `IT-PROC`, and `VEN-CON` were used to measure category retrieval. This showed that many earlier failures were evaluation issues rather than missing documents. |
| Run 3 | 25/30 passes (83.3%) | The citation pipeline and evaluator were corrected: raw retrieval evidence was separated from citations, refusal scoring was limited to unanswerable cases, and answerable cases required retrieval, support, and expected keywords. This run still used the Day 14 similarity-search baseline and identified the remaining false refusals. |
| Run 4 — Day 15 MMR | 28/30 passes (93.3%) | Retrieval changed from similarity search with `k=3` to MMR with `k=5` and `fetch_k=20`. The evaluation set was also corrected so the missing probation-policy question is treated as unanswerable. MMR improved context diversity and reduced false refusals. |

### Run 1: Initial evaluation problems

The first saved baseline run passed only **4 of 30** cases. This was not a reliable measure of RAG quality because the evaluation did not yet distinguish between:

- raw documents retrieved by FAISS,
- citations attached to a supported answer, and
- a deliberate refusal with no citations.

The pipeline correctly returned no citations for an unsupported answer, but the evaluator interpreted empty citations as failed retrieval. This made deliberate refusals and answerable questions with citation-metadata issues appear to be retrieval failures.

### Run 2: Source-category tracking

The second saved baseline run improved to **20 of 30** passes after source handling was made explicit.

The following changes made category-level retrieval measurable:

- source metadata was normalized to filenames with `Path(...).name`;
- category prefixes were mapped to the expected test category;
- matching was made case-insensitive;
- the FAISS query embedding model was kept aligned with the index model, `text-embedding-3-small`.

This prevented false misses caused by full file paths, missing `filename` metadata, and casing differences.

### Run 3: Corrected Day 14 baseline evaluation

The third run reached **25 of 30** passes. The main changes were evaluation correctness fixes:

```python
retrieved_sources: list[str] = Field(default_factory=list)
```

`retrieved_sources` records all FAISS results even when the model refuses. In contrast, `citations` remains empty for a refusal, preserving citation integrity.

The evaluator was also changed so that:

- answerable questions pass only when retrieval, support, and expected keywords all pass;
- deliberately unanswerable questions pass when the model correctly refuses;
- `correctly_refused` is not reported as `True` for answerable cases;
- retrieval quality is measured against raw retrieved sources rather than answer citations.

The reported Run 3 result preceded the final test-case correction for the probation-policy question. Because the source documents contain no probation-policy content, that case belongs in the unanswerable group.

### Run 4: Day 15 MMR retrieval

Run 4 is the current Day 15 result: **28 of 30** passes.

Instead of selecting only the nearest chunks, MMR selects relevant chunks while reducing redundancy. The expanded, more diverse context resolved several false refusals from the similarity-search baseline.

The remaining failures are no longer document-category retrieval misses. Both have the correct category in the retrieved source list:

- the 90-day onboarding question was refused despite retrieving an HR-policy document;
- the annual-leave and carry-over answer was incomplete, so it missed the expected numeric keyword.

---

## 1. Objective

Day 14 used standard similarity search with three retrieved chunks. Some answerable questions were refused even when a document from the correct category was retrieved. The likely cause was that the top results contained duplicate or non-supporting chunks, leaving the model without the exact policy section needed to answer.

Day 15 tests **Maximum Marginal Relevance (MMR)** retrieval to improve the diversity of the context supplied to the model.

---

## 2. Retrieval Configuration

The same FAISS index and Azure embedding deployment were used. The index was built with `text-embedding-3-small`, and the same model was used for retrieval queries to keep the query vectors compatible with the stored vectors.

```python
docs = self.vectorstore.max_marginal_relevance_search(
    query,
    k=5,
    fetch_k=20,
)
```

| Setting | Value |
|---|---|
| Retrieval strategy | Maximum Marginal Relevance (MMR) |
| Returned chunks (`k`) | 5 |
| Candidates considered (`fetch_k`) | 20 |
| Vector store | FAISS |
| Embedding model | `text-embedding-3-small` |

MMR balances relevance with diversity. It first considers the 20 most relevant candidate chunks, then selects five chunks that are both relevant to the question and less redundant with one another.

---

## 3. Evaluation Improvements

The evaluation now separates retrieval evidence from user-facing citations.

`retrieved_sources` records every document returned by FAISS, including when the model refuses to answer. `citations` remains empty for a refusal so the pipeline never fabricates evidence for an unsupported answer.

This distinction makes the metrics meaningful:

- **Retrieval hit rate** checks whether the expected document category was retrieved.
- **Groundedness rate** checks whether the final answer was supported by retrieved text.
- **Refusal accuracy** checks only deliberately unanswerable questions.
- **Overall pass rate** requires retrieval, support, and expected keywords for answerable questions; it requires a correct refusal for unanswerable questions.

The probation-policy question was also corrected to `expected_supported: false`, because no probation-policy content exists in the source documents.

---

## 4. What the Results Show

The pipeline retrieved a document from the expected category for all 23 answerable questions:

```text
Retrieval hit rate: 23 / 23 = 100%
```

It also refused all seven unanswerable questions without hallucinating:

```text
Refusal accuracy: 7 / 7 = 100%
```

The overall score of 28/30 shows that MMR produced a strong and diverse retrieval context for most questions. However, a correct document category is not the same as retrieving the exact supporting chunk. The remaining failures demonstrate why chunk-level inspection is still necessary.

---

## 5. Remaining Failures

### Q1: 90-day onboarding programme

The retrieval step included `HR-POL-002_Recruitment_and_Selection.pdf`, the expected HR-policy source, but the model returned the standard refusal.

The source document contains the answer:

> The onboarding programme spans 90 days and includes mandatory compliance training in weeks 1 and 4.

This is a false refusal. The retrieved result came from the correct document category, but the exact onboarding chunk may not have been included among the five selected chunks, or the model did not identify it in the supplied context.

### Q2: Annual leave over five years and carry-over

The pipeline returned an incomplete answer:

```text
- Annual leave: Employees with
```

The answer was considered grounded because it overlapped with a retrieved annual-leave chunk, but it did not include the expected `25` days or the five-day carry-over limit. This is an output-completeness failure rather than a category-retrieval failure.

The next diagnostic step is to inspect the Responses API completion status and incomplete details. The current request uses `max_output_tokens=500`; increasing that limit and recording response status will determine whether the output was truncated.

---

## 6. Important MMR Limitation

`max_marginal_relevance_search()` returns documents, not the original FAISS similarity scores. The Day 15 pipeline therefore assigns `0.0` when it converts documents into `(document, score)` pairs for compatibility with the citation code.

Any displayed `0.000` score in the Day 15 context is a placeholder, not an MMR relevance score, and should not be used to judge retrieval quality.

---

## 7. Next Steps

1. Preserve Day 14 as the similarity-search baseline and save Day 15 results separately.
2. Record the Day 15 output in `evaluations/day15_mmr_results.json` rather than overwriting the baseline result file.
3. Log the retrieved chunk text or a short preview for failed questions, not only the document filename.
4. Check the Azure Responses completion status for incomplete answers and consider increasing `max_output_tokens` from 500 to 1,000.
5. Tune the MMR relevance/diversity trade-off with `lambda_mult` (for example, `0.7`) after establishing this `k=5`, `fetch_k=20` result as the first MMR benchmark.

---

## Conclusion

MMR retrieval achieved a **93.3% overall pass rate**, with perfect document-category retrieval and perfect refusal behavior. The remaining two failures are focused, diagnosable issues: one false refusal despite the correct document category and one incomplete answer. The experiment demonstrates that retrieval diversity improves RAG reliability, while also showing that document-level retrieval metrics must be complemented by chunk-level and output-completeness checks.
