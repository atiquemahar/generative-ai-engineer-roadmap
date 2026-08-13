# projects/knowledge_agent/api/routers/knowledge.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from functools import lru_cache
from projects.knowledge_agent.schema.knowledge import KnowledgeQueryRequest, KnowledgeQueryResponse
from projects.knowledge_agent.agent.knowledge_agent import KnowledgeAgent

router = APIRouter()
@lru_cache(maxsize=1)
def get_knowledge_agent() -> KnowledgeAgent:
    return KnowledgeAgent()

@router.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge(
    request: KnowledgeQueryRequest,
    agent: KnowledgeAgent = Depends(get_knowledge_agent)
):
    try:
        result = await run_in_threadpool(
            agent.ask,
            question=request.prompt,
            k=request.top_k
        )
        return KnowledgeQueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge retrieval error: {str(e)}")