"""
shared/ingestion/loaders.py
Day 10 — Document Loaders (Docling — single loader for all formats)
 
Docling natively handles every format used in this project:
  .pdf   ✓  (layout-aware, table-preserving, OCR fallback)
  .docx  ✓  (Office Open XML)
  .txt   ✓  (plain text)
  .md    ✓  (Markdown with heading hierarchy)
 
One loader. No dispatch table. No per-format branches.
 
Install:
    pip install langchain-docling docling
 
Folder for the 15 enterprise documents (relative to repo root):
    data/enterprise_docs/
        hr_policies/          ← HR-POL-001/002/003.pdf
        it_procedures/        ← IT-PROC-001/002/003.docx
        expense_guidelines/   ← FIN-EXP-001/002/003.txt
        leave_policies/       ← HR-LEA-001/002/003.md
        vendor_contracts/     ← VEN-CON-001/002/003.pdf
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from langchain_core.documents import Document

# Formats Docling supports that are relevant to this project
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# ─────────────────────────────────────────────────────────────────────────────
# Core loader — Docling handles all formats
# ─────────────────────────────────────────────────────────────────────────────

def load_document(path: str) -> list[Document]:
    """
    Load any supported document using DoclingLoader.
 
    Docling handles PDF, DOCX, TXT, and Markdown through a single unified
    pipeline — no per-format branching needed. It auto-detects the format
    from the file extension and selects the appropriate backend internally.
 
    Args:
        path: Absolute or relative path to the document.
 
    Returns:
        List of LangChain Document objects with metadata:
            filename   — basename of the source file
            doc_type   — extension without dot (pdf, docx, txt, md)
            loader     — "docling" (always)
            loaded_at  — ISO-8601 UTC timestamp
 
    Raises:
        FileNotFoundError: file does not exist
        ValueError:        unsupported extension
        ImportError:       langchain-docling not installed
    """
    try:
        from langchain_docling import DoclingLoader
    except ImportError:
       raise ImportError(
            "langchain-docling is not installed.\n"
            "Run: pip install langchain-docling docling"
       )
    file_path = Path(path)
    if not file_path.exists:
        raise FileNotFoundError(f"file not found {path}")
    
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported extension '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        ) 
    # DoclingLoader accepts file path and auto-detects format.
    # export_type="markdown" (default) gives structured text with
    # heading markers preserved — ideal for heading-aware chunking on Day 11.

    loader = DoclingLoader(file_path=file_path)
    docs = loader.load()

    # Enrich metadata — DoclingLoader already sets 'source'; add our keys.
    loaded_at = datetime.now(timezone.utc).isoformat()
    for doc in docs:
        doc.metadata["filename"] = file_path.name
        doc.metadata["doc_type"] =suffix.lstrip(".")
        doc.metadata["loader"] = "docling" 
        doc.metadata["loaded_at"] = loaded_at

    return docs    
       
def load_directory(
        dir_path: str, 
        recursive: bool =False, 
        extensions: Optional[list[str]] =None,
    ) -> list[Document]:
    """
    Load all supported documents in a directory using DoclingLoader.
 
    Args:
        dir_path:   Path to the directory (e.g. "data/enterprise_docs").
        recursive:  Walk subdirectories if True.
        extensions: Whitelist of extensions; defaults to all supported ones.
 
    Returns:
        Flat list of Documents with a 'source' metadata key (full path).
    """
    root = Path(dir_path)
    if not root.is_dir:
        raise NotADirectoryError(f"Not a directory: {dir_path}")
    
    allowed = set(extensions or SUPPORTED_EXTENSIONS)
    glob_pattern = "**/*" if recursive else "*"
 
    all_docs: list[Document] = []
    failed: list[tuple[str, str]] = []
 
    for file_path in sorted(root.glob(glob_pattern)):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in allowed:
            continue
 
        try:
            docs = load_document(str(file_path))
            char_count = sum(len(d.page_content) for d in docs)
            for doc in docs:
                doc.metadata["source"] = str(file_path)
            all_docs.extend(docs)
            print(
                f"  ✓ {file_path.name:<50} "
                f"{len(docs):>2} doc(s)  {char_count:>8,} chars"
            )
        except Exception as exc:  # noqa: BLE001
            failed.append((file_path.name, str(exc)))
            print(f"  ✗ {file_path.name} — {exc}")
 
    if failed:
        print(f"\n⚠  {len(failed)} file(s) failed:")
        for name, err in failed:
            print(f"   {name}: {err}")
 
    return all_docs
           