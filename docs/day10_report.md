# Day 10: Advanced Document Ingestion & Layout-Aware Parsing

## Overview
Implemented a unified, layout-aware data ingestion pipeline using Docling, replacing basic LangChain document loaders. Both the original (`document_loader.py`) and upgraded (`day10_document_loader.py`) scripts are retained in this commit to demonstrate the evolution of the chunking strategy.

## Key Engineering Upgrades
- **Semantic Chunking:** Replaced basic LangChain loaders with Docling for layout-aware parsing.
- **Unified Pipeline:** Built a single ingestion script to seamlessly handle PDFs, Word docs (`.docx`), Markdown (`.md`), and Text (`.txt`) files.
- **Automated Metadata:** Added automated metadata extraction (`filename` and `doc_type`) to all document chunks to support downstream vector database filtering.
- **Improved Density:** Improved chunking density by breaking files down by structural elements (tables, paragraphs, headers) instead of rigid physical page boundaries.
- **Optimized Execution:** Enabled local CPU caching for RapidOCR and Layout Heron models, drastically reducing PDF processing times after the initial "cold start."

## Performance Comparison: Basic Loaders vs. Docling

### 1. Chunking Strategy (20 vs. 104 Documents)
*   **Basic Loaders:** Produced 20 large documents. Text/Word files were loaded as single massive strings, and PDFs were rigidly cut by page boundaries. 
*   **Docling Pipeline:** Produced 104 semantic documents. The layout-aware model successfully recognized tables, lists, and headers, resulting in cleaner, bite-sized chunks that are highly optimized for RAG (Retrieval-Augmented Generation) LLM context windows.

### 2. Processing Speeds & Caching
*   **Initial PDF (Cold Start):** ~20 minutes to download and initialize the OCR/Layout models into local memory.
*   **Subsequent PDFs (Cached):** ~8.5 seconds per file.
*   **Native Text Formats (DOCX, MD, TXT):** ~2.1 seconds per file, as they bypass the OCR engine entirely and parse the native digital structure.

### 3. Text Normalization
Docling proved superior at stripping out invisible whitespace, carriage returns, and messy table formats, replacing them with clean Markdown syntax. This slightly reduced total character counts while preserving 100% of the underlying data structure, saving token costs for future agentic workflows.