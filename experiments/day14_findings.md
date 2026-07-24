# Day 14 — Citation Pipeline Findings

## Final Results (Run 2)

| Metric | Score |
|---|---|
| Answerable — supported=True | 5/5 |
| Refusal accuracy (unanswerable) | 5/5 |
| Citation integrity | ✓ No fabricated sources |

---

## 1. Why did refusal accuracy reach 5/5?

The pipeline achieved **100% refusal accuracy** because the system prompt explicitly instructed the model to answer **only** using the retrieved context documents. The prompt also required the model to return the exact response:

> *"I don't have enough information in the provided documents to answer this question."*

whenever the retrieved context did not contain sufficient information.

All five unanswerable questions (CEO salary, employee count, revenue target, IT department head, and stock ticker) were absent from the retrieved documents. Instead of hallucinating answers, the model consistently returned the predefined refusal response.

The pipeline then detected this refusal phrase and automatically set:

- `supported = False`
- `confidence = "low"`
- `citations = []`
- `unanswerable_reason = "Model could not find answer in retrieved context"`

The combination of prompt engineering and deterministic post-processing resulted in **5/5 refusal accuracy**.

---

## 2. What does overlap = 1.000 mean on Q3?

Question:

> What uptime percentage does the vendor guarantee for production workloads?

Answer:

> The vendor guarantees **99.95% monthly uptime for production workloads.**

The retrieved chunk contained almost the exact same sentence. After tokenization and stopword removal, every meaningful word in the generated answer appeared in the retrieved chunk.

For example:

```
Answer:
vendor guarantees 99.95% monthly uptime production workloads

Retrieved chunk:
vendor guarantees 99.95% monthly uptime production workloads
```

Since every meaningful token matched, the overlap ratio became:

```
7 matched words / 7 answer words = 1.000
```

An overlap score of **1.000** represents perfect lexical grounding, meaning the generated answer was completely supported by the retrieved document.

In production systems, perfect overlap typically occurs when:

- the retrieved chunk already contains the complete answer,
- the model copies the information almost verbatim,
- very little paraphrasing is performed.

Longer answers usually produce lower overlap scores because the model tends to summarize or rephrase the retrieved content.

---

## 3. The Non-Determinism Problem (Q1 across two runs)

Run 1:

```
supported = False
```

Run 2:

```
supported = True
overlap = 0.800
```

Although the question and retrieved documents were identical, the generated answers differed slightly between runs.

Large Language Models are probabilistic systems, meaning they can produce different wording for the same prompt even when the retrieved context remains unchanged.

Because the grounding algorithm compares answer words against retrieved chunk words, small wording differences can significantly affect the overlap score.

For example:

Run 1:

> Expense claims without receipts are limited to twenty-five US dollars.

Run 2:

> USD 25 per individual expense.

Although both answers express the same meaning, they contain different tokens. Since grounding is based on lexical overlap rather than semantic similarity, the overlap score may cross the grounding threshold in one run but not another.

This demonstrates how LLM output non-determinism can affect deterministic grounding metrics even when retrieval quality remains unchanged.

---

## 4. Short Numeric Answers at the Threshold Boundary

The answer to the expense policy question is very short:

> USD 25

After stopword removal, only two meaningful tokens remain:

```
{"usd", "25"}
```

With only two tokens, each token contributes **50%** of the overlap score.

This makes short numeric answers much more sensitive to formatting differences.

For example:

```
USD
vs
US$
```

or

```
25
vs
25.00
```

may reduce the overlap score even though the meaning is identical.

A fixed grounding threshold of **0.35** works well for longer descriptive answers but is less reliable for very short factual answers because a single token mismatch has a much larger impact.

A better production approach would be to:

- use adaptive thresholds based on answer length,
- normalize numbers and currency formats before comparison,
- or use semantic similarity instead of lexical overlap for short answers.

These improvements make grounding more robust for concise numerical responses.

---

## 5. Double Model Call Bug

Initially, the script called `answer_with_citations()` twice:

1. once to display the results,
2. once again while saving the JSON output.

This created a production risk because every LLM call is independent.

For example:

First call:

```
supported = True
```

Second call:

```
supported = False
```

The console output and the saved JSON could therefore contain different answers, different citations, or different confidence scores for the same question.

The duplicate model call also:

- doubled inference cost,
- increased latency,
- increased API usage,
- reduced experiment reproducibility.

### Fix Applied

The pipeline now stores every `RAGResponse` object during the evaluation loop and reuses those stored results when writing the JSON file.

This removes the second model call, guarantees that the displayed results and saved results are identical, reduces API cost, and makes the evaluation deterministic.

---

## What Day 15 Adds

Day 14 validated that the citation pipeline correctly handled both answerable and unanswerable questions while generating grounded citations.

Day 15 extends this evaluation from **10 test questions to 30 questions**, providing a more comprehensive measurement of retrieval and answer quality.

The evaluation introduces four quantitative metrics:

- **Retrieval Hit Rate** – percentage of questions where retrieval returned the correct supporting document.
- **Groundedness Rate** – percentage of generated answers supported by retrieved evidence.
- **Refusal Accuracy** – percentage of unanswerable questions correctly rejected.
- **Average Latency** – average end-to-end response time per query.

These metrics provide a more complete evaluation of retrieval performance, grounding quality, and overall RAG system reliability.