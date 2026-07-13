# api/routers/extract.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from projects.knowledge_agent.api.dependencies import get_project_client
from shared.models.complaint import Complaint
from projects.knowledge_agent.services.extractor import extract_complaint

router = APIRouter()

# Request Model specific to this incoming payload
class ExtractRequest(BaseModel):
    text_to_analyze: str

# We assign response_model directly to our domain schema 'Complaint'
@router.post("/", response_model=Complaint)
async def extract_complaint_data(
    payload: ExtractRequest,
    client = Depends(get_project_client) # <-- FastAPI builds the client here
):
    try:
        # We extract the string from the payload, and pass both it and 
        # the injected client directly into our core extraction function.
        result, _ = extract_complaint(              # unpack — ignore tokens in API route
            message=payload.text_to_analyze, 
            project_client=client
        ) 
        
        # FastAPI handles serializing this Complaint object back into JSON
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))