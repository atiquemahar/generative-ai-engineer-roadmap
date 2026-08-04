# ── Report generator ──────────────────────────────────────────────────────────

import sys
from pathlib import Path


REPORT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "evaluations" / "knowledge_agent_report.md"



def generate_report(output, failures, direct, multi, ambiguous, unanswerable, ground_dist, grounded_results):
    m = output["metrics"]
    ts = output["generated_at"]
 
    # Identify top failure patterns from failures list
    pattern1 = [r for r in failures if r["category"] == "multi_document" and r["actual_supported"] and not r["retrieval_hit"]]
    pattern1 += [r for r in failures if r["category"] == "multi_document" and not r["actual_supported"]]
    pattern2 = [r for r in failures if r["category"] == "ambiguous" and not r["actual_supported"]]
    pattern3 = [r for r in failures if r["category"] == "unanswerable" and r["actual_supported"]]
 
    lines = [
        "# Knowledge Agent Evaluation Report",
        "",
        f"**Generated:** {ts}",
        f"**Dataset:** knowledge_agent_eval_set.json ({sum(len(x) for x in [direct, multi, ambiguous, unanswerable])} questions)",
        "**Retrieval method:** hybrid_semantic (k=5)",
        "",
        "---",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value | Target |",
        "|--------|-------|--------|",
        f"| Retrieval Hit Rate @5 | {m['retrieval_hit_rate']:.0%} | > 70% |",
        f"| Retrieval Hit Rate @3 | {m['retrieval_hit_rate_at_3']:.0%} | — |",
        f"| Source Precision | {m['source_precision']:.0%} | — |",
        f"| Answer Groundedness (avg) | {m['answer_groundedness_avg']:.2f} / 3.0 | — |",
        f"| Answer Grounded (≥ 2/3) | {m['answer_grounded_pct']:.0%} | — |",
        f"| Citation Accuracy | {m['citation_accuracy']:.0%} | 100% |",
        f"| Refusal Accuracy | {m['refusal_accuracy']:.0%} | > 80% |",
        f"| Overall Pass Rate | {m['overall_pass_rate']:.0%} | — |",
        "",
        "---",
        "",
        "## Category Breakdown",
        "",
        "| Category | Count | Retrieval Hit @5 |",
        "|----------|-------|-----------------|",
        f"| Direct | {len(direct)} | {m['retrieval_hit_by_category']['direct']:.0%} |",
        f"| Multi-Document | {len(multi)} | {m['retrieval_hit_by_category']['multi_document']:.0%} |",
        f"| Ambiguous | {len(ambiguous)} | {m['retrieval_hit_by_category']['ambiguous']:.0%} |",
        f"| Unanswerable | {len(unanswerable)} | Refusal: {m['refusal_accuracy']:.0%} |",
        "",
        "---",
        "",
        "## Answer Groundedness Distribution",
        "",
        f"Evaluated on {len(grounded_results)} supported answers.",
        "",
        "| Score | Label | Count | % |",
        "|-------|-------|-------|---|",
        f"| 3 | Fully grounded | {ground_dist[3]} | {ground_dist[3]/len(grounded_results):.0%} |" if grounded_results else "| — | — | — | — |",
        f"| 2 | Mostly grounded | {ground_dist[2]} | {ground_dist[2]/len(grounded_results):.0%} |" if grounded_results else "",
        f"| 1 | Partially grounded | {ground_dist[1]} | {ground_dist[1]/len(grounded_results):.0%} |" if grounded_results else "",
        f"| 0 | Not grounded | {ground_dist[0]} | {ground_dist[0]/len(grounded_results):.0%} |" if grounded_results else "",
        "",
        "---",
        "",
        "## Citation Accuracy",
        "",
        "Citation accuracy is 100% by architectural design. The `_build_sources()` method",
        "constructs the citation list directly from the list returned by `HybridSearcher`.",
        "The LLM is never asked to generate source references — it produces answer text only.",
        "This design makes source fabrication structurally impossible regardless of prompt.",
        "",
        "---",
        "",
        "## Top 3 Failure Patterns",
        "",
    ]
 
    # Pattern 1
    lines += [
        "### Pattern 1 — Cross-domain retrieval miss",
        "",
        "**Affected questions:** multi_document category",
        "",
        "When a question spans two departments (e.g. HR + IT, or two vendor contracts),",
        "the less semantically obvious document gets crowded out of the top-5 by",
        "same-domain content. The embedding vector skews toward the more prominent domain",
        "and the secondary document never scores high enough to be retrieved.",
        "",
        "**Root cause:** k=5 is insufficient when both expected sources need to rank in the",
        "top half of results for different sub-domains. No prompt change can fix a retrieval miss.",
        "",
        "**Potential fix:** increase k to 8 for multi-part queries, or apply a department",
        "filter to force coverage of each required domain in separate retrieval passes.",
        "",
    ]
    if pattern1:
        lines.append("**Affected questions:**")
        lines.append("")
        for r in pattern1[:3]:
            lines.append(f"- [{r['id']:02d}] {r['question']}")
            lines.append(f"  - Expected: {r['expected_sources']}")
            lines.append(f"  - Retrieved: {r['actual_sources']}")
            lines.append("")
 
    # Pattern 2
    lines += [
        "### Pattern 2 — Short/ambiguous query over-refusal",
        "",
        "Short, ambiguous questions do not give the embedding model enough signal.",
        "The retrieved chunks may contain the relevant policy section but the LLM",
        "evaluates each chunk as not fully answering the question and refuses.",
        "",
        "**Root cause:** very short queries produce low-precision embeddings that",
        "retrieve broadly relevant but not pinpoint-accurate chunks. The grounding",
        "guardrail then correctly rejects an answer that would require inference,",
        "but the context actually does contain the answer in a specific subsection.",
        "",
        "**Potential fix:** query expansion — rewrite short queries before embedding",
        "to add context clues, or use a dedicated 'question type' classifier to",
        "route ambiguous questions to a broader context window.",
        "",
    ]
    if pattern2:
        lines.append("**Affected questions:**")
        lines.append("")
        for r in pattern2[:3]:
            lines.append(f"- [{r['id']:02d}] {r['question']}")
            lines.append(f"  - Retrieval: {r['chunks_retrieved']} chunks retrieved, supported=False")
            lines.append("")
 
    # Pattern 3
    lines += [
        "### Pattern 3 — Topical inference hallucination",
        "",
        "The LLM sets `supported=True` for a question that is technically unanswerable",
        "because retrieved chunks are topically related but do not explicitly state",
        "the requested policy. The 'explicitly state' guardrail in the system prompt",
        "catches most cases but fails when the semantic overlap is genuine.",
        "",
        "**Root cause:** the corpus contains partial policy coverage that overlaps",
        "with out-of-scope topics. For example, remote work arrangements partially",
        "resemble flexible hours. The LLM finds a plausible answer and misidentifies",
        "it as explicitly stated.",
        "",
        "**Potential fix:** add a validation step that confirms the answer text",
        "contains explicit policy language (numbers, named sections, dates) rather",
        "than general statements. Unanswerable questions tend to produce vaguer answers.",
        "",
    ]
    if pattern3:
        lines.append("**Affected questions:**")
        lines.append("")
        for r in pattern3[:3]:
            lines.append(f"- [{r['id']:02d}] {r['question']}")
            lines.append(f"  - Answer: {r['actual_answer'][:120]}...")
            lines.append(f"  - Sources cited: {r['actual_sources']}")
            lines.append("")
 
    # All failures
    if failures:
        lines += [
            "---",
            "",
            "## Failed Questions Detail",
            "",
        ]
        for r in failures:
            lines += [
                f"### [{r['id']:02d}] [{r['category']}]",
                "",
                f"**Question:** {r['question']}",
                f"**Expected sources:** {r['expected_sources']}",
                f"**Returned sources:** {r['actual_sources']}",
                f"**Expected supported:** {r['expected_supported']}",
                f"**Actual supported:** {r['actual_supported']} (confidence: {r['actual_confidence']})",
                f"**Answer:** {r['actual_answer'][:200]}{'...' if len(r['actual_answer']) > 200 else ''}",
                "",
            ]
 
    lines += [
        "---",
        "",
        "## Recommendations",
        "",
        "1. **Increase k for multi-part queries.** Set k=8 when the query contains",
        "   conjunctions ('and', 'both', 'as well as') or explicitly spans multiple topics.",
        "",
        "2. **Query expansion for short queries.** Queries under 8 words should be",
        "   expanded before embedding to improve retrieval precision.",
        "",
        "3. **Secondary groundedness check for unanswerable detection.** Before",
        "   returning supported=True, verify the answer contains at least one explicit",
        "   policy marker (a number, date, named section, or specific dollar amount).",
        "   Answers without these markers on policy questions are likely inferences.",
        "",
    ]
 
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))