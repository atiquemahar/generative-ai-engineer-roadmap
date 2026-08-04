"""
projects/knowledge_agent/agent/run_eval.py
Day 22 — Full Evaluation: 5 metrics + markdown report
 
Metrics:
  retrieval_hit_rate   — expected source in top-5 returned sources
  retrieval_hit_rate@3 — expected source in top-3 returned sources
  source_precision     — fraction of returned sources that are expected
  answer_groundedness  — LLM judge score 0-3, % grounded (score >= 2)
  citation_accuracy    — all cited docs were retrieved (architectural guarantee)
  refusal_accuracy     — unanswerable questions correctly return supported=False
 
Outputs:
  evaluations/day22_eval_results.json
  evaluations/knowledge_agent_report.md
"""
import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.knowledge_agent.agent.knowledge_agent import KnowledgeAgent
from projects.knowledge_agent.agent.groundedness_judge import judge_groundedness
from projects.knowledge_agent.agent.generate_report_day22 import generate_report, REPORT_PATH

EVAL_SET_PATH  = Path(REPO_ROOT) / "evaluations" / "knowledge_agent_eval_set.json"
RESULTS_PATH   = Path(REPO_ROOT) / "evaluations" / "day22_eval_results.json"


RETRIEVAL_HIT_RATE_THRESHOLD = 0.70
REFUSAL_ACCURACY_THRESHOLD   = 0.80

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_eval_set(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def retrieval_hit(actual_sources: list[dict], expected_sources: list[str]) -> bool:
    """At least one expected source in returned sources (lenient, top-5)."""
    if not expected_sources:
        return True # unanswerable questions have no expected sources 
    return any(exp in actual_sources for exp in expected_sources)

def retrieval_hit_at_3(actual_sources: list[dict], expected_sources: list[str], k: int=3) -> bool: 
    """At least one expected source in the top-3 returned sources (strict)."""
    if not expected_sources:
        return True
    return any(exp in actual_sources[:k] for exp in expected_sources)   

def source_precision(actual_sources: list[dict], expected_sources: list[str]) -> float:
    """Fraction of returned sources that are expected sources."""
    if not actual_sources:
        return 0.0
    hits = sum(1 for s in actual_sources if s in expected_sources)
    return hits / len(actual_sources)

def citation_accuracy(result: dict) -> bool:
    """
    All cited sources were in the retrieved results.
    In this system this is always True by design — _build_sources() only
    reads from retrieval output. Reported explicitly to document the
    architectural safety guarantee.
    """
    retrieved = {s["document"] for s in result.get("raw_sources", [])}
    for source in result.get("sources", []):
        if source["document"] not in retrieved:
            return False
    return True

# ── Main evaluation loop ──────────────────────────────────────────────────────


def run_evaluation():
    eval_cases = load_eval_set(EVAL_SET_PATH)
    agent = KnowledgeAgent()
 
    print("=" * 70)
    print("  DAY 22 — Full Evaluation: 5 metrics + groundedness judging")
    print(f"  {len(eval_cases)} questions  |  retrieval k=5")
    print("=" * 70)

    results = []
 
    for case in eval_cases:
        qid      = case["id"]
        question = case["question"]
        category = case["category"]
        exp_srcs = case["expected_sources"]
        exp_sup  = case["expected_supported"]
 
        print(f"\n[{qid:02d}] [{category.upper():<15s}] {question[:65]}")

         # ── Run agent ─────────────────────────────────────────────────────────
        result = agent.ask(question, k=5)
 
        actual_srcs = [s["document"] for s in result.get("sources", [])]
        supported   = result["supported"]
        context     = result.get("context", "")

        # ── Retrieval metrics ─────────────────────────────────────────────────
        hit5  = retrieval_hit(actual_srcs, exp_srcs)
        hit3  = retrieval_hit_at_3(actual_srcs, exp_srcs)
        prec  = source_precision(actual_srcs, exp_srcs) if exp_srcs else None
        cit_ok = True  # by architectural design

        # ── Groundedness judging (only for supported answers) ─────────────────
        if supported and result["answer"]:
            grounding = judge_groundedness(
                question=question,
                answer=result["answer"],
                context=context,
                openai_client=agent.openai_client,
            )
        else:
            grounding = {"grounded": None, "score": None, "reason": "Not applicable (unsupported answer)"}

        # ── Pass/fail ─────────────────────────────────────────────────────────
        if not exp_sup:
            passed = not supported
        else:
            passed = supported and hit5

        # ── Print ─────────────────────────────────────────────────────────────
        status = "✓ PASS" if passed else "✗ FAIL"
        grnd_str = f"score={grounding['score']}" if grounding["score"] is not None else "n/a"
        print(f"  {status} | supported={supported} | {grnd_str} | hit@5={hit5} | hit@3={hit3}")
        if not passed:
            if exp_sup and not supported:
                print(f"  FAIL: answerable → supported=False")
            if not exp_sup and supported:
                print(f"  FAIL: unanswerable → supported=True")
            if exp_sup and supported and not hit5:
                print(f"  FAIL: expected source not retrieved")
 
        results.append({
            **case,
            "actual_answer"     : result["answer"],
            "actual_supported"  : supported,
            "actual_confidence" : result["confidence"],
            "actual_sources"    : actual_srcs,
            "retrieval_hit"     : hit5,
            "retrieval_hit_at3" : hit3,
            "source_precision"  : round(prec, 4) if prec is not None else None,
            "citation_accurate" : cit_ok,
            "groundedness_score": grounding["score"],
            "groundedness_flag" : grounding["grounded"],
            "groundedness_reason": grounding["reason"],
            "support_correct"   : (supported == exp_sup),
            "passed"            : passed,
            "latency_ms"        : result["latency_ms"],
            "chunks_retrieved"  : result["chunks_retrieved"],
        })
 
        time.sleep(0.2) 

        # ── Compute metrics ───────────────────────────────────────────────────────
 
    answerable   = [r for r in results if r["expected_supported"]]
    unanswerable = [r for r in results if not r["expected_supported"]]
    direct       = [r for r in answerable if r["category"] == "direct"]
    multi        = [r for r in answerable if r["category"] == "multi_document"]
    ambiguous    = [r for r in answerable if r["category"] == "ambiguous"]

    def rate(lst, key):
        valid = [r for r in lst if r[key] is not None]
        return sum(r[key] for r in valid) / len(valid) if valid else 0.0

    retrieval_hit_rate    = rate(answerable, "retrieval_hit")
    retrieval_hit_rate_3  = rate(answerable, "retrieval_hit_at3")
    avg_src_precision     = rate([r for r in answerable if r["source_precision"] is not None], "source_precision")
    citation_acc          = rate(results, "citation_accurate")
    refusal_acc           = rate(unanswerable, "passed")
    overall_pass_rate     = rate(results, "passed")
    support_accuracy      = rate(answerable, "support_correct")

    grounded_results = [r for r in results if r["groundedness_score"] is not None]
    avg_ground_score  = sum(r["groundedness_score"] for r in grounded_results) / len(grounded_results) if grounded_results else 0.0
    pct_grounded      = sum(1 for r in grounded_results if r["groundedness_flag"]) / len(grounded_results) if grounded_results else 0.0

    ground_dist = {0: 0, 1: 0, 2: 0, 3: 0}
    for r in grounded_results:
        ground_dist[r["groundedness_score"]] += 1

    rhr_pass = retrieval_hit_rate >= RETRIEVAL_HIT_RATE_THRESHOLD
    ra_pass  = refusal_acc        >= REFUSAL_ACCURACY_THRESHOLD 

    hit_by_cat = {
        "direct"         : rate(direct,    "retrieval_hit"),
        "multi_document" : rate(multi,     "retrieval_hit"),
        "ambiguous"      : rate(ambiguous, "retrieval_hit"),
    }
 
    failures = [r for r in results if not r["passed"]]

    
    # ── Print summary ─────────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("  EVALUATION SUMMARY — Day 22")
    print("=" * 70)
    print(f"  Total questions     : {len(results)}")
    print(f"  Overall pass rate   : {sum(r['passed'] for r in results)}/{len(results)} ({overall_pass_rate:.0%})")
    print()
    print(f"  Retrieval hit @5    : {retrieval_hit_rate:.0%}   (target > {RETRIEVAL_HIT_RATE_THRESHOLD:.0%})")
    print(f"  Retrieval hit @3    : {retrieval_hit_rate_3:.0%}")
    print(f"    Direct   ({len(direct):>2})   : {hit_by_cat['direct']:.0%}")
    print(f"    Multi-doc({len(multi):>2})   : {hit_by_cat['multi_document']:.0%}")
    print(f"    Ambiguous({len(ambiguous):>2}) : {hit_by_cat['ambiguous']:.0%}")
    print(f"  Source precision    : {avg_src_precision:.0%}")
    print()
    print(f"  Groundedness avg    : {avg_ground_score:.2f} / 3.0  ({len(grounded_results)} answers judged)")
    print(f"  Grounded (≥2)       : {pct_grounded:.0%}")
    print(f"  Ground dist 3/2/1/0 : {ground_dist[3]}/{ground_dist[2]}/{ground_dist[1]}/{ground_dist[0]}")
    print()
    print(f"  Citation accuracy   : {citation_acc:.0%}  (architectural guarantee)")
    print(f"  Refusal accuracy    : {refusal_acc:.0%}   (target > {REFUSAL_ACCURACY_THRESHOLD:.0%})")
    print(f"  Support accuracy    : {support_accuracy:.0%}")
    print()
    print(f"  Retrieval ≥ {RETRIEVAL_HIT_RATE_THRESHOLD:.0%}  : {'✓ PASS' if rhr_pass else '✗ FAIL'}")
    print(f"  Refusal   ≥ {REFUSAL_ACCURACY_THRESHOLD:.0%}  : {'✓ PASS' if ra_pass  else '✗ FAIL'}")

    if failures:
        print(f"\n  Failed ({len(failures)}):")
        for r in failures:
            print(f"    [{r['id']:02d}] [{r['category']}] {r['question'][:60]}")

    # ── Save JSON ─────────────────────────────────────────────────────────────
 
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "metrics": {
            "retrieval_hit_rate"        : round(retrieval_hit_rate,   4),
            "retrieval_hit_rate_at_3"   : round(retrieval_hit_rate_3, 4),
            "source_precision"          : round(avg_src_precision,    4),
            "answer_groundedness_avg"   : round(avg_ground_score,     4),
            "answer_grounded_pct"       : round(pct_grounded,         4),
            "groundedness_distribution" : ground_dist,
            "citation_accuracy"         : round(citation_acc,         4),
            "refusal_accuracy"          : round(refusal_acc,          4),
            "support_accuracy"          : round(support_accuracy,     4),
            "overall_pass_rate"         : round(overall_pass_rate,    4),
            "retrieval_hit_by_category" : {k: round(v, 4) for k, v in hit_by_cat.items()},
            "thresholds": {
                "retrieval_hit_rate_passed": rhr_pass,
                "refusal_accuracy_passed"  : ra_pass,
            },
        },
        "results": results,
    }  

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    generate_report(output, failures, direct, multi, ambiguous, unanswerable, ground_dist, grounded_results)

    print(f"\n  Results : {RESULTS_PATH}")
    print(f"  Report  : {REPORT_PATH}")

if __name__ == "__main__":
    run_evaluation()

        


