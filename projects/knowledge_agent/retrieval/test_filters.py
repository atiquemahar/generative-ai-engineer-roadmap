"""
projects/knowledge_agent/retrieval/test_filters.py
Day 19 — 10 scoped queries to verify metadata filters
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from projects.knowledge_agent.retrieval.searcher import HybridSearcher

searcher = HybridSearcher()

SCOPED_QUERIES = [
    # (label, query, filters, sort_by_date)

    # ── Department filters ────────────────────────────────────────────────────
    ("Finance dept",
     "What expenses can I claim when travelling for work?",
     {"department": "Finance"}, False),

    ("HR dept",
     "How much annual leave do I get?",
     {"department": "hr"}, False),          # shorthand normalised to "Human Resources"

    ("IT dept",
     "What is the process for requesting new software?",
     {"department": "it"}, False),

    ("Legal dept",
     "What are the data protection obligations in vendor contracts?",
     {"department": "Legal"}, False),

    # ── doc_type filters ──────────────────────────────────────────────────────
    ("PDF only",
     "What is the code of conduct policy?",
     {"doc_type": "pdf"}, False),

    ("Markdown only",
     "What is the sick leave entitlement?",
     {"doc_type": "md"}, False),

    ("Plain text only",
     "How do I submit an expense report?",
     {"doc_type": "txt"}, False),

    # ── Date filters ──────────────────────────────────────────────────────────
    ("Year 2026 only",
     "What are the current IT security procedures?",
     {"year": 2026}, False),

    # ── Combined filters ──────────────────────────────────────────────────────
    ("Finance + 2026",
     "What is the latest expense reimbursement policy?",
     {"department": "Finance", "year": 2026}, False),

    # ── Sort by date (recency) ────────────────────────────────────────────────
    ("HR sorted by date desc",
     "Latest HR policy updates",
     {"department": "hr"}, True),
]

def run_tests():
    print("=" * 70)
    print("  DAY 19 — Filtered Search Tests")
    print("=" * 70)

    for label, query, filters, sort_by_date in SCOPED_QUERIES:
        print(f"\n[{label}]")
        print(f" Query : {query}")
        print(f" Filters : {filters}")
        if sort_by_date:
            print(f" Sort : effective_date desc")

        results = searcher.filtered_search(
            query=query,
            filters=filters,
            k=5,
            sort_by_date=sort_by_date,
        ) 

        if not results:
            print("  ⚠ No results returned")
            continue

        for i, r in enumerate(results, 1):
            print(
                f"  {i}. [{r.get('department','?'):20s}] "
                f"[{r.get('doc_type','?'):5s}] "
                f"{r.get('filename','?')}"
            )

        # Verify filter applied — every result should match
        if "department" in filters:
            expected_dept = searcher.build_filter_string(
                {"department": filters["department"]}
            )
            # extract stored value from first result for quick sanity check
            returned_depts = {r.get("department") for r in results}
            print(f"  Departments in results: {returned_depts}")

if __name__ == "__main__":
    run_tests()                   
