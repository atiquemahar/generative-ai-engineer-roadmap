import os
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_core.documents import Document

def load_document(path: str) -> list[Document]:
    suffix = Path(path).suffix.lower()
    # Initialize the correct loader based on file type
    if suffix == ".pdf":
        loader = PyMuPDFLoader(path)
    elif suffix == ".docx":
        loader = Docx2txtLoader(path)
    elif suffix in [".txt", ".md"]:
        # Explicitly setting utf-8 fixes the Windows text loading error
        loader = TextLoader(path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    docs = loader.load()
    # Add metadata to each doc: filename, doc_type, loaded_at
    for doc in docs:
        doc.metadata["filename"] = Path(path).name
        doc.metadata["doc_type"] = suffix.strip(".")
    return docs

def load_directory(directory_path):
    all_documents = []

    if not os.path.isdir(directory_path):
        raise ValueError(f"The directory '{directory_path}' does not exist")
    
    print(f"Scanning directory: {directory_path}\n")

    # os.walk automatically goes into your subfolders
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Extract the subfolder name to use as a category tag
            # e.g., turns ".../enterprise_docs/hr_policies" into "hr_policies"
            category = os.path.basename(root)
            try:
                # Call your existing load_document function
                docs = load_document(file_path)

                # If your load_document function returns objects (like LangChain Documents),
                # you can inject the category into the metadata here before saving:
                # if isinstance(docs, list):
                #     for doc in docs:
                #         doc.metadata['category'] = category

                if isinstance(docs, list):
                    all_documents.extend(docs)
                elif docs:
                    all_documents.append(docs)

                print(f"Loaded: [{category}] {file}")

            except Exception as e:
                print(f"Error loading {file}: {e}")

    print(f"\nTotal documents loaded: {len(all_documents)}")
    return all_documents

# This tells Python to actually execute the code when you run the file directly
if __name__ == "__main__":
    
    # Get the folder where THIS loader.py file lives
    current_script_path = Path(__file__).parent
    
    # Go up two levels (to generative-ai-engineer-roadmap) then into data/enterprise_docs
    target_folder = current_script_path.parent.parent / "data" / "enterprise_docs"
    
    print("Starting document ingestion pipeline...")
    print(f"Looking for folder exactly at: {target_folder}")
    
    # Convert Path object to string just to be safe for os.walk
    my_enterprise_docs = load_directory(str(target_folder))
    
    print("Pipeline finished successfully!")
    print("\n" + "="*75)
    print(" DOCUMENT VERIFICATION REPORT")
    print("="*75)
    
    # 1. Aggregate stats by filename
    file_stats = {}
    all_metadata_present = True
    
    for doc in my_enterprise_docs:
        # 2. Verify metadata is present on EVERY document chunk
        if "filename" not in doc.metadata or "doc_type" not in doc.metadata:
            all_metadata_present = False
            
        filename = doc.metadata.get("filename", "Unknown")
        char_count = len(doc.page_content)
        
        # Initialize the file in our dictionary if it's the first time we see it
        if filename not in file_stats:
            file_stats[filename] = {"pages": 0, "chars": 0}
            
        # Add the page and character counts
        file_stats[filename]["pages"] += 1
        file_stats[filename]["chars"] += char_count

    # 3. Print the formatted table
    print(f"{'Filename':<55} | {'Pages':<5} | {'Characters':<10}")
    print("-" * 75)
    
    for fname, stats in file_stats.items():
        print(f"{fname:<55} | {stats['pages']:<5} | {stats['chars']:<10}")
        
    print("-" * 75)
    print(f"Total Unique Files Processed: {len(file_stats)}")
    
    if all_metadata_present:
        print("✅ Metadata Verification: 'filename' and 'doc_type' present on ALL documents.")
    else:
        print("❌ Metadata Verification: WARNING - Some documents are missing metadata!")             
    

