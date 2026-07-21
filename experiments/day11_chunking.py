import os
import sys
import csv
from pathlib import Path
from langchain_core.documents import Document

from langchain_text_splitters import  RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load 15 documents using your basic loader
from shared.ingestion.document_loader import load_directory

DOCS_ROOT = Path(REPO_ROOT) / "data" / "enterprise_docs"

# Define 4 strategies
STRATEGIES = {
    "fixed_500_no_overlap": RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0),
    "fixed_500_overlap_100": RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100),
    "small_200_overlap_50": RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50),
    "heading_aware_md": MarkdownHeaderTextSplitter(headers_to_split_on=[("#","H1"),("##","H2")])
}

QUESTIONS_WITH_ANSWERS = [
    {"question": "What is the maximum expense claim without a receipt?",
     "expected_source": "expense_guidelines"},    # which subfolder should answer it
    {"question": "How many days of annual leave does a new employee get?",
     "expected_source": "leave_policies"},
    {"question": "What VPN software is approved for remote access?",
     "expected_source": "it_procedures"},
    {"question": "How much fee customer will pay to Vendor on monthly base?",
     "expected_source": "vendor_contracts"},
    {"question": "After how much day of invoice Payment will be due",
     "expected_source": "vendor_contracts"},
    {"question": "How many days of Paid Sick Leave does an employee 3 years of experience get?",
     "expected_source": "leave_policies"},
    {"question": "what is the code of conduct for Social Media and public Communication use?",
     "expected_source": "hr_policies"},
    {"question": "what is the Shortlisting criteria?",
     "expected_source": "hr_policies"},
    {"question": "what is the Offer and Onboarding policy?",
     "expected_source": "hr_policies"},     
]

def keyword_score(query: str, chunk_text: str) -> int:
    """Simple word overlap score — same as Day 9."""
    query_words = set(query.lower().split())
    chunk_words = set(chunk_text.lower().split())
    return len(query_words & chunk_words)

def retrieval_hit(qusetion: str, expected_source: str, chunks: list[Document], top_k: int = 3) -> bool:
    """Check if top_k retrieved chunks contain the expected source category."""
    scored = [(keyword_score(qusetion, c.page_content), c) for c in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    for score, chunk in top:
        # Check if the expected_source folder appears in the metadata
        source = chunk.metadata.get("source", "") or chunk.metadata.get("filename", "")
        if expected_source in source and score > 0:
            return True
    return False

if __name__ == "__main__":
    print("Loading 15 enterprise documents...")
    all_docs = load_directory(str(DOCS_ROOT))
    print(f"Loaded {len(all_docs)} documents\n")

    results = []
    # Separate markdown docs for heading-aware splitting
    md_docs = [d for d in all_docs if d.metadata.get("doc_type") == "md"]
    non_md_docs = [d for d in all_docs if d.metadata.get("doc_type") != "md"]

    for strategy_name, splitter in STRATEGIES.items():
        print(f"Testing strategy: {strategy_name}")
        if strategy_name == "heading_aware_md":
            # MarkdownHeaderTextSplitter uses split_text not split_documents
            # Apply only to .md files
            chunks = []
            for doc in md_docs:
                split_docs = splitter.split_text(doc.page_content)
                # split_text returns Documents but without source metadata — add it back
                for split_doc in split_docs:
                    split_doc.metadata.update(doc.metadata)
                chunks.extend(split_docs)
            print(f"  Chunks produced: {len(chunks)} (from {len(md_docs)} markdown docs only)")
        else:
            chunks = splitter.split_documents(all_docs)
            print(f"  Chunks produced: {len(chunks)}")

        hits = 0
        for qa in QUESTIONS_WITH_ANSWERS:
            hit = retrieval_hit(qa["question"], qa["expected_source"], chunks)
            if hit:
                hits += 1

        avg_size = sum(len(c.page_content) for c in chunks) / len(chunks) if chunks else 0
        results.append({
            "strategy": strategy_name,
            "chunks": len(chunks),
            "avg_chunk_size": round(avg_size),
            "questions_answered": hits,
            "accuracy": f"{hits}/{len(QUESTIONS_WITH_ANSWERS)}"
        }) 
    # Save CSV
    csv_path = REPO_ROOT / "experiments" / "day11_chunking_comparison.csv"  
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["strategy", "chunks", "avg_chunk_size", "questions_answered", "accuracy"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*55}")
    print("CHUNKING COMPARISON")
    print(f"{'='*55}")
    print(f"{'Strategy':<30} {'Chunks':>6} {'Avg Size':>9} {'Answered':>9}")
    for r in results:
        print(f"{r['strategy']:<30} {r['chunks']:>6} {r['avg_chunk_size']:>9} {r['accuracy']:>9}")

    print(f"\nResults saved to: {csv_path}")                  



