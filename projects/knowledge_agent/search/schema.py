"""
projects/knowledge_agent/search/schema.py
Day 16/17: index schema — Day 18: adds semantic configuration
"""

from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,   # Day 18 additions
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)

INDEX_NAME = "enterprise-knowledge"
SEMANTIC_CONFIG_NAME = "knowledge-semantic-config"   # Day 18

FOLDER_TO_DEPARTMENT = {
    "hr_policies": "Human Resources",
    "it_procedures": "Information Technology",
    "expense_guidelines": "Finance",
    "leave_policies": "Human Resources",
    "vendor_contracts": "Legal" 
}

def build_index() -> SearchIndex:
    """
    Build the Azure AI Search index schema with vector field.
    1536 dimensions matches text-embedding-3-small output.
    """
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.STRING,
            key=True,
            facetable=True,
        ),
        SearchableField(name="content"    
        ),
        SearchField(
          name="content_vector",
          type=SearchFieldDataType.Collection(SearchFieldDataType.SINGLE),
          searchable=True,
          vector_search_dimensions=1536,
          vector_search_profile_name="hnsw-profile",  
        ),
        SimpleField(
            name="filename",
            type=SearchFieldDataType.STRING,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="doc_type",
            type=SearchFieldDataType.STRING,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.INT32,
            filterable=True,
        ),
        SimpleField(
            name="heading",
            type=SearchFieldDataType.STRING,
        ),
        SimpleField(
            name="department",
            type=SearchFieldDataType.STRING,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="effective_date",
            type=SearchFieldDataType.DATE_TIME_OFFSET,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.STRING,
            filterable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(
            name="hnsw-profile",
            algorithm_configuration_name="hnsw-algo",
        )

        ]
    )

    # Day 18 — semantic configuration
    # content is the primary field the reranker reads.
    # heading and department provide keyword signals for reranking.

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="heading"),
                        SemanticField(field_name="department"),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )