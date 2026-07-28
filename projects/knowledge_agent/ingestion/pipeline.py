"""
projects/knowledge_agent/ingestion/pipeline.py
Day 17 — Indexing Pipeline
 
Loads all 15 enterprise documents via Docling, chunks them, generates
embeddings with text-embedding-3-small, and uploads to Azure AI Search
with full metadata and duplicate detection.
 
Install:
    pip install azure-search-documents azure-identity langchain-docling docling
 
Run:
    python projects/knowledge_agent/ingestion/pipeline.py
"""

import os
import re
import sys
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from langchain_openai import AzureOpenAI
from langchain_openai import AzureOpenAIEmbeddings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(Path(REPO_ROOT) / ".env")

from shared.ingestion.docling_loader import load_document
from projects.knowledge_agent.search.schema import (
    INDEX_NAME,
    FOLDER_TO_DEPARTMENT,
    build_index,
)

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]  # https://knowledgebas.search.windows.net
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]  # Primary admin key from portal

openai_client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview",
)

EMBEDDING_DEPLOYMENT = os.environ["AZURE_EMBEDDING_DEPLOYMENT"]

# ── Effective dates per document prefix (matches filenames) ───────────────────

EFFECTIVE_DATES = {
    "HR-POL": "2026-03-01T00:00:00Z",
    "IT-PROC": "2026-01-01T00:00:00Z",
    "FIN-EXP": "2026-01-01T00:00:00Z",
    "HR-LEA":  "2026-01-01T00:00:00Z",
    "VEN-CON": "2026-02-01T00:00:00Z",
}

DOCS_ROOT = Path(REPO_ROOT) / "data" / "enterprise_docs"

# Helpers

def clean_text(text: str) -> str:
    """Remove excess whitespace and normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text) # collapse 3+ blank lines to 2
    text = re.sub(r"[ \t]{2,}", " ", text) # collapse multiple spaces/tabs
    return text.strip()

def make_chunk_id(filename: str, chunk_index: int) -> str:
    """
    Deterministic chunk ID from filename + index.
    Same file + same chunk position always produces the same ID.
    This is what enables duplicate detection on re-indexing.
    """
    raw = f"{filename}::chunk::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()

def get_effective_date(filename: str) -> str:
    for prefix, date in EFFECTIVE_DATES.items():
        if filename.upper().startswith(prefix):
            return date
    return "2026-01-01T00:00:00Z"

def get_heading(text: str) -> str:
    """
    Extract the first heading-like line from chunk text.
    Docling preserves Markdown headings (# H1, ## H2) for MD files,
    and uses bold/caps lines for PDF/DOCX headings.
    """
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#'):
            return line.lstrip('#').strip()
        if line and line.isupper() and len(line) > 5:
            return line.title()
    return ""

def embed_text(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings in batches of 16 to stay within API limits.
    text-embedding-3-small returns 1536-dimensional vectors.
    """

    
    embedding_client = AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        model=EMBEDDING_DEPLOYMENT,
        api_version="2025-04-01-preview",
    ) 
    all_embeddings: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        batch_embeddings = embedding_client.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        if i + batch_size < len(texts):
            time.sleep(0.5)
    return all_embeddings        



# IndexingPipeline

class IndexingPipeline:
    def __init__(self, search_client: SearchClient):
        self.search_client = search_client

    def process_document(self, path: str) -> list[dict]:
        """
        1. Load with Docling
        2. Clean text
        3. Each Docling chunk becomes one index document
        4. Add all metadata fields
        5. Generate embeddings
        6. Return list of index-ready dicts
        """
        file_path = Path(path) 
        filename = file_path.name
        suffix = file_path.suffix.lower().lstrip(".")
        folder = file_path.parent.name
        department = FOLDER_TO_DEPARTMENT.get(folder, "General")

        # Step 1: load — Docling splits into semantic chunks
        langchain_docs = load_document(str(file_path)) 

        # Step 2 + 3: clean and build index documents (without embeddings yet)
        index_docs = []
        text_for_embedding = []

        for i, doc in enumerate(langchain_docs):
            content = clean_text(doc.page_content) 
            if not content:
                continue  # skip empty chunks

            chunk_id = make_chunk_id(filename, i)

            index_doc = {
                "id": chunk_id, #key filed
                "content": content,
                "filename": filename,
                "doc_type": suffix,
                "page_number": int(doc.metadata.get("page", i)),
                "heading": get_heading(content),
                "department": department,
                "effective_date": get_effective_date(filename),
                "chunk_id": chunk_id,
                # content_vector added after embedding
            }
            index_docs.append(index_doc)
            text_for_embedding.append(content)

        if text_for_embedding:
            embeddings = embed_text(text_for_embedding) 
            for doc, vector in zip(index_docs, embeddings):
                doc["content_vector"] = vector
        return index_docs

    def duplicate_check(self, chunk_id: str) -> bool:
        """
        Check if chunk_id already exists in the index.
        One API call per chunk — acceptable for 15 documents.
        For production scale, replace with batch existence check
        using a single filter: id in ('id1', 'id2', ...)
        """
        try:
            results = self.search_client.search(
                search_text="*",
                filter=f"chunk_id eq '{chunk_id}'",
                select=["chunk_id"],
                top=1
            )
            return any(True for _ in results)
        except Exception:
            return False   # if check fails, allow upload (safer than skipping)

    def index_document(self, path: str) -> dict:
        """
        Full pipeline for one file: process → deduplicate → upload.
        Returns a summary dict.
        """
        docs = self.process_document(path)
        new_docs = [d for d in docs if not self.duplicate_check(d["chunk_id"])]
        skipped = len(docs) - len(new_docs)

        if new_docs:
            # Upload in batches of 100 (Azure AI Search limit per request)
            batch_size = 100
            for i in range(0, len(new_docs), batch_size):
                batch = new_docs[i: i + batch_size] 
                self.search_client.upload_documents(documents=batch) 

        return {
            "file":    Path(path).name,
            "total":   len(docs),
            "new":     len(new_docs),
            "skipped": skipped,
        }  

# Index creation (idempotent — skips if already exists)

def ensure_index_exists():
    """
    Create the Azure AI Search index if it doesn't exist.
    Safe to call on every run — skips creation if index already exists.
    This is the proper SDK-based index creation that includes content_vector.
    """
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    ) 
    existing = [idx.name for idx in index_client.list_indexes()] 
    if INDEX_NAME in existing:
        print(f"Index '{INDEX_NAME}' already exists — skipping creation.")
        return

    index = build_index()
    index_client.create_index(index)  
    print(f"Index '{INDEX_NAME}' created with vector field (1536 dims).")

# Main

if __name__ == "__main__":
    print("=" * 65)
    print("  DAY 17 — Indexing Pipeline")
    print(f"  Documents root: {DOCS_ROOT}")
    print("=" * 65)

    # Step 1: ensure index exists with vector field
    ensure_index_exists()

    # Step 2: build search client
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_API_KEY),
    )

    pipeline = IndexingPipeline(search_client)

    # Step 3: index all 15 documents

    all_files = sorted(DOCS_ROOT.rglob("*"))
    all_files =[
        f for f in all_files
        if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
    ]

    print(f"\nFound {len(all_files)} documents to index.\n")
    print(f"{'File':<52} {'Total':>6} {'New':>5} {'Skip':>6}")
    print("-" * 70)

    total_chunks = 0
    total_new = 0
    total_skip = 0
    failed = []

    for file_path in all_files:
        try: 
            result = pipeline.index_document(str(file_path))
            total_chunks += result["total"]
            total_new += result["new"]
            total_skip += result["skipped"]
            print(
                f"  ✓ {result['file']:<50} {result['total']:>6} "
                f"{result['new']:>5} {result['skipped']:>6}"
            )
        except Exception as e:
            failed.append((file_path.name, str(e))) 
            print(f"  ✗ {file_path.name:<50} ERROR: {e}")

    # Step 4: summary
    print("-" * 70)
    print(f"  {'TOTAL':<50} {total_chunks:>6} {total_new:>5} {total_skip:>6}")
    print(f"\n  Chunks indexed : {total_new}")
    print(f"  Chunks skipped : {total_skip} (already in index)")
    print(f"  Failures       : {len(failed)}")

    if failed:
        print("\nFailed files:")
        for name, err in failed:
            print(f"  {name}: {err}")

    # Step 5: duplicate detection test — run counts again
    print("\n" + "=" * 65)
    print("  DUPLICATE DETECTION TEST")
    print("  Re-indexing first document — expect 0 new, all skipped.")
    print("=" * 65)

    if all_files:
        test_result = pipeline.index_document(str(all_files[0]))
        print(f"  File    : {test_result['file']}")
        print(f"  Total   : {test_result['total']}")
        print(f"  New     : {test_result['new']}    ← should be 0")
        print(f"  Skipped : {test_result['skipped']} ← should equal Total")
        passed = test_result["new"] == 0
        print(f"  Result  : {'✓ PASS' if passed else '✗ FAIL'}")

    print(f"\nVerify in portal:")
    print(f"  Search explorer → search=* → check document count")
    print(f"  Filter test: $filter=department eq 'Finance'")
    print(f"  Filter test: $filter=doc_type eq 'pdf'")                       



                           