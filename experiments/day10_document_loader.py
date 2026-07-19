"""
experiments/day10_document_loaders.py
Day 10 — Test DoclingLoader against all 15 enterprise documents.

Run from repo root:
    python experiments/day10_document_loaders.py

Expected: filename, doc count, char count, metadata check for all 15 docs.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.ingestion.document_loader import load_document, load_directory

# Documents live here (relative to repo root):
#   data/enterprise_docs/hr_policies/
#   data/enterprise_docs/it_procedures/
#   ...
# Change this:
# DOCS_ROOT = REPO_ROOT / "data" / "enterprise_docs"

# To this:
DOCS_ROOT = Path(REPO_ROOT) / "data" / "enterprise_docs"

REQUIRED_METADATA = {"filename", "doc_type", "loader", "loaded_at"}


def main() -> None:
    print("=" * 65)
    print("  DAY 10 — DoclingLoader Test (single loader, all formats)")
    print(f"  Docs root: {DOCS_ROOT}")
    print("=" * 65)

    if not DOCS_ROOT.exists():
        print(f"\n❌ Directory not found: {DOCS_ROOT}")
        print("   Place the 15 enterprise docs under data/enterprise_docs/")
        sys.exit(1)

    categories = {
        "HR Policies      (.pdf) ": DOCS_ROOT / "hr_policies",
        "IT Procedures    (.docx)": DOCS_ROOT / "it_procedures",
        "Expense Guides   (.txt) ": DOCS_ROOT / "expense_guidelines",
        "Leave Policies   (.md)  ": DOCS_ROOT / "leave_policies",
        "Vendor Contracts (.pdf) ": DOCS_ROOT / "vendor_contracts",
    }

    results = []
    warnings = []

    for label, folder in categories.items():
        print(f"\n── {label} ──")
        if not folder.exists():
            print(f"   ⚠  Folder missing: {folder}")
            continue

        for fp in sorted(folder.iterdir()):
            if not fp.is_file():
                continue
            t0 = time.perf_counter()
            try:
                docs = load_document(str(fp))
                ms = (time.perf_counter() - t0) * 1000
                chars = sum(len(d.page_content) for d in docs)

                missing = [
                    f"doc#{i}: {REQUIRED_METADATA - set(d.metadata)}"
                    for i, d in enumerate(docs)
                    if REQUIRED_METADATA - set(d.metadata)
                ]
                if missing:
                    warnings.extend(
                        [f"{fp.name} — missing metadata: {m}" for m in missing]
                    )

                results.append(
                    dict(name=fp.name, typ=fp.suffix.lstrip("."),
                         docs=len(docs), chars=chars, ms=round(ms), ok=True)
                )
                preview = docs[0].page_content[:120].replace("\n", " ").strip()
                print(f"  ✓ {fp.name}")
                print(f"    docs={len(docs)} | chars={chars:,} | {ms:.0f}ms")
                print(f"    preview: \"{preview}…\"")

            except Exception as exc:  # noqa: BLE001
                ms = (time.perf_counter() - t0) * 1000
                results.append(
                    dict(name=fp.name, typ=fp.suffix.lstrip("."),
                         docs=0, chars=0, ms=round(ms), ok=False, err=str(exc))
                )
                print(f"  ✗ {fp.name} — {exc}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  {'Filename':<46} {'Type':<5} {'Docs':>4} {'Chars':>8} {'ms':>5}")
    print(f"  {'-'*46} {'-'*5} {'-'*4} {'-'*8} {'-'*5}")
    for r in results:
        ok = "✓" if r["ok"] else "✗"
        print(f"  {ok} {r['name']:<44} {r['typ']:<5} {r['docs']:>4} "
              f"{r['chars']:>8,} {r['ms']:>4}ms")

    total_docs  = sum(r["docs"]  for r in results)
    total_chars = sum(r["chars"] for r in results)
    failures    = sum(1 for r in results if not r["ok"])

    print(f"\n  Files processed : {len(results)}")
    print(f"  Total LangChain documents : {total_docs}")
    print(f"  Total characters          : {total_chars:,}")
    print(f"  Failures                  : {failures}")

    if warnings:
        print(f"\n⚠  Metadata warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   {w}")
    else:
        print("\n  ✅ All metadata keys present on every document.")


if __name__ == "__main__":
    main()