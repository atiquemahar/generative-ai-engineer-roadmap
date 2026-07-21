import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv()

# Use Docling from here on — semantic chunks, no splitter needed
from shared.ingestion.docling_loader import load_directory

DOCS_ROOT = Path(REPO_ROOT) / "data" / "enterprise_docs"


def get_embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        openai_api_version="2025-04-01-preview",
    )

def keyword_search(query: str, docs: list[Document], top_k: int =3) -> list[Document]:
    """Same keyword overlap from Day 11 — used as baseline."""
    query_words = set(query.lower().split())
    scored = []
    for doc in docs:
        doc_words = set(doc.page_content.lower().split())
        score = len(query_words & doc_words)
        scored.append((score,doc))
    scored.sort(key=lambda x: x[0], reverse=True)    
    return [doc for score, doc in scored[:top_k] if score > 0]

def semantic_search(query: str, vectorstore: FAISS, k: int =3) -> list[Document]:
    """Vector similarity search."""
    results = vectorstore.similarity_search_with_score(query, k=k)
    return [doc for doc, score in results]

QUESTIONS = [
    {"question": "What is the maximum expense claim without a receipt?",
     "expected_source": "expense_guidelines"},
    {"question": "How many days of annual leave does a new employee get?",
     "expected_source": "leave_policies"},
    {"question": "What VPN software is approved for remote access?",
     "expected_source": "it_procedures"},
    {"question": "How much fee will the customer pay to the Vendor monthly?",
     "expected_source": "vendor_contracts"},
    {"question": "After how many days of invoice will payment be due?",
     "expected_source": "vendor_contracts"},
    {"question": "How many days of Paid Sick Leave does an employee with 3 years experience get?",
     "expected_source": "leave_policies"},
    {"question": "What is the code of conduct for Social Media and public Communication?",
     "expected_source": "hr_policies"},
    {"question": "What is the Shortlisting criteria?",
     "expected_source": "hr_policies"},
    {"question": "What is the Offer and Onboarding policy?",
     "expected_source": "hr_policies"},

    # expense_guidelines (FIN-EXP-001)
    {"question": "Within how many days must expenses be submitted after they are incurred?",
     "expected_source": "expense_guidelines"},
    {"question": "What is the personal car mileage reimbursement rate?",
     "expected_source": "expense_guidelines"},

    # expense_guidelines (FIN-EXP-002)
    {"question": "What is the one-time home office setup allowance for remote workers?",
     "expected_source": "expense_guidelines"},
    {"question": "What monthly internet stipend is provided to approved remote workers?",
     "expected_source": "expense_guidelines"},

    # expense_guidelines (FIN-EXP-003)
    {"question": "What is the annual professional development budget for an individual contributor?",
     "expected_source": "expense_guidelines"},
    {"question": "How much bonus does NovaTech pay for passing an associate-level certification exam?",
     "expected_source": "expense_guidelines"},

    # leave_policies (HR-LEA-002)
    {"question": "After how many consecutive days of absence must an employee submit a medical certificate?",
     "expected_source": "leave_policies"},
    {"question": "How many Keeping in Touch days can an employee work during parental leave?",
     "expected_source": "leave_policies"},

    # vendor_contracts (VEN-CON-001)
    {"question": "What uptime percentage does the vendor guarantee for production workloads?",
     "expected_source": "vendor_contracts"},
    {"question": "Where must customer data be stored under the data protection clause?",
     "expected_source": "vendor_contracts"},

    # it_procedures (IT-PROC-003)
    {"question": "What is the response SLA for a P1 Critical IT incident?",
     "expected_source": "it_procedures"},
]

def check_hit(retrieved: list[Document], expected_source: str) -> bool:
    for doc in retrieved:
        source = doc.metadata.get("source", "") or doc.metadata.get("filename", "")
        if expected_source in source:
            return True
    return False

if __name__ == "__main__":
    print("Loading documents with Docling...")
    t0 = time.perf_counter()
    docs = load_directory(str(DOCS_ROOT), recursive=True)
    print(f"Loaded {len(docs)} semantic chunks in {time.perf_counter()-t0:.1f}s\n")

    print("Building FAISS index with Azure embeddings...")
    embeddings = get_embeddings()
    t0 = time.perf_counter()
    vectorstore = FAISS.from_documents(docs, embeddings)
    print(f"Index built in {time.perf_counter()-t0:.1f}s\n")

    print(f"{'='*60}")
    print(f"{'Question':<45} {'Keyword':>8} {'Semantic':>9}")
    print(f"{'-'*45} {'-'*8} {'-'*9}")

    keyword_hits = 0
    semantic_hits = 0

    for qa in QUESTIONS:
        kw_results = keyword_search(qa["question"], docs)
        sem_results = semantic_search(qa["question"], vectorstore)

        kw_hit = check_hit(kw_results, qa["expected_source"])
        sem_hit = check_hit(sem_results, qa["expected_source"])

        if kw_hit : keyword_hits +=1
        if sem_hit: semantic_hits +=1

        kw_str = "✓" if kw_hit else "✗"
        sem_str = "✓" if sem_hit else "✗"
        print(f"{qa['question'][:44]:<45} {kw_str:>8} {sem_str:>9}")

    print(f"{'-'*60}")
    print(f"{'TOTAL':<45} {keyword_hits}/20   {semantic_hits}/20")

    # Save FAISS index for Day 13 — no re-embedding needed
    index_path = Path(REPO_ROOT) / "experiments" / "retrieval" / "faiss_index"
    index_path.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_path))
    print(f"\nFAISS index saved to: {index_path}")




 