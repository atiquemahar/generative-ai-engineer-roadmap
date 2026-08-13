# projects/knowledge_agent/schema/knowledge.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class KnowledgeQueryRequest(BaseModel):
    prompt: str = Field(..., example="What is the standard probation period for new hires?")
    top_k: Optional[int] = Field(default=3, ge=1, le=10)

class SourceMetadata(BaseModel):
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    relevance_score: Optional[float] = None

class KnowledgeQueryResponse(BaseModel):
    answer: str
    sources: List[SourceMetadata] 
    confidence: Optional[str] = None      