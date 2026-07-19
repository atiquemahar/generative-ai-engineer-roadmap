# Day 09 — Keyword RAG Failures

## Questions That Failed Retrieval

- **When will I receive my refund?** → no documents retrieved
- **What happens if my product breaks?** → no documents retrieved

## Analysis


The keyword-based retrieval failed on these inputs because it relies on **exact string matching** (set intersection) of raw words. It lacks the ability to process variations in text, exposing three major limitations of basic keyword search:

1. **Punctuation Interference:** The `split()` method attaches adjacent punctuation to words. In the first query, the code searches for `"refund?"` (with a question mark), which will never match the document's `"refunds"`. Likewise, `"receive"` does not match `"received."` (with a period).
2. **Morphology and Pluralization:** Keyword matching treats singular and plural forms as completely distinct words. The user asked about a `"product"` and `"refund"`, but the documents contained `"products"` and `"refunds"`. Without stemming or lemmatization, the system sees zero overlap.
3. **Lack of Semantic Understanding:** Exact keyword matching cannot understand intent or synonyms. For the second query, a human knows that a product that `"breaks"` is related to documents about being `"repaired or replaced"`. However, because the exact word "breaks" does not appear in the warranty text, the system fails to retrieve the highly relevant document.

**Conclusion:** 
To build a robust RAG pipeline, raw keyword matching is insufficient. We need text normalization (stripping punctuation, stemming) or, ideally, **Semantic Search (Vector Embeddings)** which maps queries and documents based on meaning rather than exact spelling.
