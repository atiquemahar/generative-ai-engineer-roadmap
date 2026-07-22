# Day 12 — Semantic vs Keyword Search Findings

## Results
| Method   | Score |
|----------|-------|
| Keyword  | 15/20 |
| Semantic | 20/20 |

## Why Keyword Failed on 5 Questions

| Question | Keyword Failure Reason |
|---|---|
| What VPN software is approved for remote access? | Document only mentions VPN clients are *prohibited* — "approved" never appears near "VPN" |
| How much fee will the customer pay to the Vendor monthly? | Document uses "base fee" and "monthly" but "customer" + "vendor" + "fee" don't co-occur in same chunk |
| How many days of Paid Sick Leave does an employee with 3 years experience get? | Document says "3+" and "entitlement" — "3 years" and "get" have zero overlap |
| What is the code of conduct for Social Media and public Communication? | Heading capitalisation differs; content words don't overlap with the short query |
| What is the Shortlisting criteria? | "Shortlisting" appears as a heading but body content words don't match the query tokens |

## Root Cause
Every failure is a vocabulary mismatch — the user's words and the document's words
are different strings representing the same concept. Keyword search scores zero
on these. Semantic search handles all 5 because embeddings capture meaning, not
character overlap.

Examples:
- "fee" ↔ "service charge" — different strings, same concept
- "VPN software" ↔ "Cisco AnyConnect" — different strings, same concept
- "3 years experience" ↔ "3+ years" — different strings, same threshold

## Index Saved
FAISS index saved to: experiments/retrieval/faiss_index/
Load on Day 13 with FAISS.load_local() — no re-embedding needed.

## Note on the 9/11 Split
The first 9 questions were written earlier and happen to use closer document
vocabulary — keyword scored 8/9 on those. The remaining 11 used more natural
phrasing — keyword dropped to 7/11, semantic scored 11/11.
This wasn't a deliberate experimental design; it's a pattern observed after
the fact. The overall 15/20 vs 20/20 result is what matters.