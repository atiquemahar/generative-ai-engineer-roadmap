from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from projects.knowledge_agent.api.dependencies import get_project_client
import os

# 1. Initialize the mini-router instead of the global 'app
router = APIRouter()

# 2. Request Model: Defines what the incoming JSON payload MUST look like
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Optional field, defaults to None if missing

# 3. Response Model: Defines what data is allowed to leave the API
class ChatResponse(BaseModel):
    reply: str
    session_id: Optional[str] = None
    status: str = "success"

# 4. Route Decorator: Notice we use @router.post instead of @app.post
# The path is just "/" because the prefix will be handled globally in main.py
@router.post("/", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    project_client = Depends(get_project_client)   # <--- FastAPI injects the dependency here, AIProjectClient, not OpenAI client
): 
    try:

        model = os.environ.get("MODEL_DEPLOYMENT_NAME")
        if not model:
            raise ValueError("Missing MODEL_DEPLOYMENT_NAME")
        
        with project_client.get_openai_client() as client: # get OpenAI client here
            response = client.responses.create(
                model=model,
                instructions="you are helpful assistant",
                input=request.message,
                max_output_tokens=500,
            )

        
        # Build and return the response data matching ChatResponse shape
        return ChatResponse(
            reply=response.output_text,
            session_id=request.session_id,
        ) 
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat generation failed: {str(e)}")


