"""
projects/knowledge_agent/agent/run_eval.py
Day 21 — 50-Question Evaluation Runner
 
Metrics computed:
  retrieval_hit_rate  — for answerable questions, at least one expected source
                        appears in the returned sources. Target: > 0.70
  full_recall_rate    — all expected sources appear in returned sources.
  refusal_accuracy    — unanswerable questions correctly return supported=False.
                        Target: > 0.80
  support_accuracy    — answerable questions correctly return supported=True.
 
Results saved to: evaluations/day21_eval_results.json
"""

import os
import sys
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.knowledge_agent.agent.knowledge_agent import KnowledgeAgent

EVAL_SET_PATH  = Path(REPO_ROOT) / "evaluations" / "knowledge_agent_eval_set.json"
RESULTS_PATH   = Path(REPO_ROOT) / "evaluations" / "day21_eval_results.json"

RETRIEVAL_HIT_RATE_THRESHOLD = 0.70
REFUSAL_ACCURACY_THRESHOLD   = 0.80

def load_eval_set(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def retrieval_hit(result: dict, expected_sources: list[str]) -> bool:
    """
    Lenient hit: at least one expected source appears in the returned sources.
    Used for retrieval_hit_rate — the primary Day 21 metric.
    """
    if not expected_sources:
        return True # unanswerable questions have no expected sources
    returned = {s["document"] for s in result.get("sources", [])} 
    return all(exp in returned for exp in expected_sources)

def full_recall(result: dict, expected_sources: list[str])  -> bool:
    """
    Strict hit: all expected sources appear in the returned sources.
    Matters most for multi_document questions.
    """
    if not expected_sources:
        return True
    returned = {s["document"] for s in result.get("sources", [])}
    return all(exp in returned for exp in expected_sources)

def run_evaluation():
    eval_cases = load_eval_set(EVAL_SET_PATH)
    agent      = KnowledgeAgent()

    print("=" * 70)
    print("  DAY 21 — 50-Question Knowledge Agent Evaluation")
    print(f"  Dataset: {EVAL_SET_PATH.name}")
    print("=" * 70)

    results = []

    for case in eval_cases:
        qid = case["id"]
        question = case["question"]
        category = case["category"]
        exp_srcs = case["expected_sources"]  
        exp_sup = case["expected_supported"]

        print(f"\n[{qid:02d}] [{category.upper():<15s}] {question[:70]}")

        result = agent.ask(question, k=5)

        hit = retrieval_hit(result, exp_srcs)
        recall = full_recall(result, exp_srcs)
        sup_ok = result["supported"] == exp_sup

        # For unanswerable: pass = correctly refused (supported=False, no sources)
        # For answerable  : pass = supported=True AND retrieval hit
        if not exp_sup:
            passed = not result["supported"]
        else:
            passed = result["supported"] and hit  

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} | supported={result['supported']} | confidence={result['confidence']}")
        print(f"  Sources returned : {[s['document'] for s in result['sources']]}")
        if exp_srcs:
            print(f"  Sources expected : {exp_srcs}")

        if not passed:
            if exp_sup and not result["supported"]:
                print(f"  FAIL: answerable question returned supported=False")
            if not exp_sup and result["supported"]:
                print(f"  FAIL: unanswerable question returned supported=True")
            if exp_sup and result["supported"] and not hit:
                print(f"  FAIL: correct source not in returned sources")
        results.append({
            **case,
            "actual_answer": result["answer"],
            "actual_supported": result["supported"],
            "actual_confidence": result["confidence"],
            "actual_sources": [s["document"] for s in result["sources"]],
            "retrieval_hit": hit,
            "full_recall": recall,
            "support_correct": sup_ok,
            "passed": passed,
            "latency_ms": result["latency_ms"],
            "chunks_retrieved": result["chunks_retrieved"],
        }) 

        time.sleep(0.2) # light rate-limit buffer between questions

    # ── Compute metrics ───────────────────────────────────────────────────────

    answerable = [r for r in results if r["expected_supported"]]
    unaswerable = [r for r in results if not r["expected_supported"]]
    direct = [r for r in answerable if r["category"] == "direct"]
    multi = [r for r in answerable if r["category"] == "multi_document"]
    ambiguous = [r for r in answerable if r["category"] == "ambiguous"]

    def rate(lst, key):
        return sum(r[key] for r in lst) /len(lst) if lst else 0.0

    retrieval_hit_rate = rate(answerable, "retrieval_hit")
    full_recall_rate = rate(answerable, "full_recall")
    refusal_accuracy = rate(unaswerable, "passed")
    support_accuracy = rate(answerable, "support_correct")
    overall_pass_rate = rate(results, "passed")

    avg_latency = sum(r["latency_ms"] for r in results) /len(results)

    hit_by_cat = {
        "direct": rate(direct, "retrieval_hit"),
        "multi_document": rate(multi, "retrieval_hit"),
        "ambiguous": rate(ambiguous, "retrieval_hit"),
    }

    # ── Print summary ─────────────────────────────────────────────────────────
 
    print("\n" + "=" * 70)
    print("  EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Total questions          : {len(results)}")
    print(f"  Overall pass rate        : {sum(r['passed'] for r in results)}/{len(results)} ({overall_pass_rate:.0%})")
    print()
    print(f"  Retrieval hit rate       : {retrieval_hit_rate:.0%}  (target > {RETRIEVAL_HIT_RATE_THRESHOLD:.0%})")
    print(f"    Direct   ({len(direct):>2} Qs)    : {hit_by_cat['direct']:.0%}")
    print(f"    Multi-doc({len(multi):>2} Qs)    : {hit_by_cat['multi_document']:.0%}")
    print(f"    Ambiguous({len(ambiguous):>2} Qs) : {hit_by_cat['ambiguous']:.0%}")
    print(f"  Full recall rate         : {full_recall_rate:.0%}  (all expected sources found)")
    print()
    print(f"  Refusal accuracy         : {refusal_accuracy:.0%}  (target > {REFUSAL_ACCURACY_THRESHOLD:.0%})")
    print(f"  Support accuracy         : {support_accuracy:.0%}  (answerable → supported=True)")
    print()
    print(f"  Avg latency              : {avg_latency:.0f} ms")

    # Threshold check
    print()
    rhr_pass = retrieval_hit_rate >= RETRIEVAL_HIT_RATE_THRESHOLD
    ra_pass  = refusal_accuracy   >= REFUSAL_ACCURACY_THRESHOLD
    print(f"  Retrieval hit rate ≥ {RETRIEVAL_HIT_RATE_THRESHOLD:.0%}  : {'✓ PASS' if rhr_pass else '✗ FAIL — do not proceed to Day 22'}")
    print(f"  Refusal accuracy   ≥ {REFUSAL_ACCURACY_THRESHOLD:.0%}  : {'✓ PASS' if ra_pass  else '✗ FAIL — improve unanswerable detection'}")

    # Failures summary
    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  Failed questions ({len(failures)}):")
        for r in failures:
            print(f"    [{r['id']:02d}] [{r['category']}] {r['question'][:65]}")

    # ── Save results ──────────────────────────────────────────────────────────
 
    output = {
        "metrics": {
            "retrieval_hit_rate"        : round(retrieval_hit_rate, 4),
            "full_recall_rate"          : round(full_recall_rate,   4),
            "refusal_accuracy"          : round(refusal_accuracy,   4),
            "support_accuracy"          : round(support_accuracy,   4),
            "overall_pass_rate"         : round(overall_pass_rate,  4),
            "avg_latency_ms"            : round(avg_latency,        1),
            "retrieval_hit_by_category" : {k: round(v, 4) for k, v in hit_by_cat.items()},
            "thresholds": {
                "retrieval_hit_rate_target"  : RETRIEVAL_HIT_RATE_THRESHOLD,
                "retrieval_hit_rate_passed"  : rhr_pass,
                "refusal_accuracy_target"    : REFUSAL_ACCURACY_THRESHOLD,
                "refusal_accuracy_passed"    : ra_pass,
            },
        },
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
 
    print(f"\n  Full results saved to: {RESULTS_PATH}")

if __name__ == "__main__":
    run_evaluation()
            
                         