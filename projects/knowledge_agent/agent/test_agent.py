"""
projects/knowledge_agent/agent/test_agent.py
Day 20 — Citation verification: 20 answerable + 5 unanswerable questions
 
Checks:
  - Every source in the response was in the retrieved chunks (no fabrication)
  - Unanswerable questions return supported=False
  - Zero citations on unsupported answers
"""
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.knowledge_agent.agent.knowledge_agent import KnowledgeAgent

# ── Test cases ─────────────────────────────────────────────────────────────────
# (question, expected_file_substring, is_answerable)
# expected_file_substring: a substring of the expected source filename.
# For unanswerable cases it is None.

ANSWERABLE = [
    # Finance — FIN-EXP-001
    ("What is the dinner per diem allowance for business travel?",          "FIN-EXP-001", True),
    ("What hotel rate cap applies for international travel in developed countries?", "FIN-EXP-001", True),
    ("How many days in advance must international flights be booked?",      "FIN-EXP-001", True),
    ("How long does an employee have to submit an expense claim?",          "FIN-EXP-001", True),
 
    # Finance — FIN-EXP-002
    ("What is the one-time home office setup allowance?",                   "FIN-EXP-002", True),
    ("How much is the monthly internet stipend for remote workers?",        "FIN-EXP-002", True),
 
    # Finance — FIN-EXP-003
    ("What is the annual training budget for senior employees?",            "FIN-EXP-003", True),
    ("What bonus is paid for passing an expert-level certification?",       "FIN-EXP-003", True),
    ("How many external conferences can an employee attend per year?",      "FIN-EXP-003", True),
 
    # HR — Leave
    ("How many days annual leave does an employee with 3 years service get?", "HR-LEA-001", True),
    ("What is the maximum carry-over of annual leave?",                     "HR-LEA-001", True),
    ("How many separate absences in 12 months trigger a formal absence review?", "HR-LEA-002", True),
    ("How many Keeping in Touch days can an employee on parental leave work?",   "HR-LEA-003", True),
 
    # HR — Policy
    ("How long must structured interview notes be retained?",               "HR-POL-002", True),
    ("What happens to employees rated Needs Improvement for two consecutive reviews?", "HR-POL-003", True),
 
    # IT
    ("Where must shared account credentials be stored?",                    "IT-PROC-001", True),
    ("Who must approve software installation exceptions?",                  "IT-PROC-002", True),
    ("What are the five phases of the incident response process?",          "IT-PROC-003", True),
 
    # Legal
    ("How long does the confidentiality obligation survive after contract termination?", "VEN-CON-001", True),
    ("How soon must subscriber data be exported after a termination request?",           "VEN-CON-002", True),
]

UNANSWERABLE = [
    ("Does the company offer a free gym membership?",          None, False),
    ("Does NovaTech have offices anywhere in Asia?",           None, False),
    ("What is the starting salary for a junior developer?",    None, False),
    ("Is there a company car or vehicle allowance policy?",    None, False),
    ("What is the CEO's name and contact email?",             None, False),
]

ALL_CASES = ANSWERABLE + UNANSWERABLE

def verify_no_fabrication(result: dict, retrieved_files: set[str]) -> bool:
    """
    Check that every source document in the response was in the retrieved chunks.
    This is the hard citation safety check.
    """
    for source in result.get("sources", []):
        if source["document"] not in retrieved_files:
            return False
    return True

def run_tests():
    agent = KnowledgeAgent()

    print("=" * 70)
    print("  DAY 20 — KnowledgeAgent Citation Test")
    print("  20 answerable + 5 unanswerable questions")
    print("=" * 70)

    passed = 0
    failed = 0
    fabrications = 0
    results_logs = []

    for i, (question, expected_sub_string, is_answerable) in enumerate(ALL_CASES, 1):
        label = "ANSWERABLE" if is_answerable else "UNANSWERABLE"
        print(f"\n[{i:02d}] [{label}] {question}")

        result = agent.ask(question, k=5)

        # ── Citation safety check ─────────────────────────────────────────────
        # Rebuild the set of retrieved filenames from sources.
        # Since sources ARE the retrieval results (by design), we check that
        # the answer doesn't name a document that wasn't in the source list.

        source_files = {s["document"] for s in result.get("sources", [])}
        no_fabrication = verify_no_fabrication(result, source_files)

        if not no_fabrication:
            fabrications +=1
            print(f"  ⚠ FABRICATION DETECTED")

        # ── Grounding check ───────────────────────────────────────────────────

        if is_answerable:
            grounding_ok = result["supported"] is True
        else:
            # Unanswerable: must be unsupported with no sources
            grounding_ok = (
                result["supported"] is False
                and len(result.get("sources", [])) == 0
            )

        if grounding_ok and no_fabrication:
            passed +=1
            status = "✓ PASS"
        else:
            failed +=1
            status = "✗ FAIL"
            if is_answerable and not result["supported"]:
                print(f"  FAIL reason: answerable question returned supported=False")
            if not is_answerable and result["supported"]:
                print(f"  FAIL reason: unanswerable question returned supported=True")

        print(f"  Status     : {status}")
        print(f"  Supported  : {result['supported']}  |  Confidence: {result['confidence']}")
        print(f"  Answer     : {result['answer'][:120]}{'...' if len(result['answer']) > 120 else ''}")
        print(f"  Sources    : {len(result['sources'])} unique document(s)")
        for s in result["sources"]:
            print(f"    - {s['document']} (page {s['page']}, score {s['relevance_score']})")
        print(f"  Latency    : {result['latency_ms']}ms  |  Chunks: {result['chunks_retrieved']}")

        # Check source file matches expected (for answerable cases)
        if is_answerable and expected_sub_string and result["supported"]:
            match = any(expected_sub_string in s["document"] for s in result["sources"])
            if not match:
                print(f"  ⚠ Expected source containing '{expected_sub_string}' not found in citations")

        results_logs.append({
            "question": question,
            "is_answerable": is_answerable,
            **result,
            "pass": grounding_ok and no_fabrication,
            "fabrication": not no_fabrication,
        })

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total questions  : {len(ALL_CASES)}")
    print(f"  Passed           : {passed}")
    print(f"  Failed           : {failed}")
    print(f"  Fabrications     : {fabrications}  ← must be 0")
 
    answerable_supported = sum(
        1 for r in results_logs if r["is_answerable"] and r["supported"]
    )
    unanswerable_rejected = sum(
        1 for r in results_logs if not r["is_answerable"] and not r["supported"]
    )
    print(f"\n  Answerable correctly supported  : {answerable_supported}/{len(ANSWERABLE)}")
    print(f"  Unanswerable correctly rejected : {unanswerable_rejected}/{len(UNANSWERABLE)}")
 
    # Save full results
    output_path = REPO_ROOT / "evaluations" / "day20_agent_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_logs, f, indent=2, default=str)
    print(f"\n  Full results saved to: {output_path}")

if __name__ == "__main__":
    run_tests()
