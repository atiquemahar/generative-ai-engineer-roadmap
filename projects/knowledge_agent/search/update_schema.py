# projects/knowledge_agent/search/update_schema.py
"""
Day 18 — Step 0: Add semantic configuration to existing index.
 
Run once before building searcher.py.
Does NOT drop or re-index — semantic config is a metadata-only change.
 
Run:
    python projects/knowledge_agent/search/update_schema.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
 
load_dotenv(REPO_ROOT / ".env")

from projects.knowledge_agent.search.schema import build_index, INDEX_NAME

index_client = SearchIndexClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    credential=AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"])
)

index_client.create_or_update_index(build_index())
print(f"Index '{INDEX_NAME}' updated — semantic configuration added.")
print("No re-indexing required. Proceed to searcher.py.")