from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.vector_memory import get_vector_memory_service, VectorMemoryService

router = APIRouter(prefix="/memory", tags=["memory"])

class MemoryAddRequest(BaseModel):
    text: str

class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 5

class MemoryQueryResponse(BaseModel):
    results: List[str]

@router.post("/add")
async def add_to_memory(
    request: MemoryAddRequest, 
    service: VectorMemoryService = Depends(get_vector_memory_service)
):
    try:
        service.add_to_memory(request.text)
        return {"status": "success", "message": "Text added to long-term memory"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=MemoryQueryResponse)
async def query_memory(
    request: MemoryQueryRequest,
    service: VectorMemoryService = Depends(get_vector_memory_service)
):
    try:
        results = service.query_memory(request.query, request.top_k)
        return MemoryQueryResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
