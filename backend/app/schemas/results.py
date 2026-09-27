from typing import List, Optional
from pydantic import BaseModel
from backend.app.schemas.candidate import CandidateSchema

class ProcessingStatusResponse(BaseModel):
    session_id: str
    status: str
    stage: str
    total: int
    processed: int
    failed: int
    shortlisted: int
    percentage: float
    error_message: Optional[str] = None

class CandidateListResponse(BaseModel):
    session_id: str
    total: int
    eligible_count: int
    shortlisted_count: int
    candidates: List[CandidateSchema]
