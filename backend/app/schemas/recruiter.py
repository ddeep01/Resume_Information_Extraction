from typing import Optional, List, Dict
from pydantic import BaseModel, Field, model_validator

class ScoringWeights(BaseModel):
    education: float = Field(default=0.35, description="Weight for education (0.0 to 1.0)")
    publication: float = Field(default=0.30, description="Weight for publications (0.0 to 1.0)")
    academic_experience: float = Field(default=0.20, description="Weight for academic experience (0.0 to 1.0)")
    industry_experience: float = Field(default=0.15, description="Weight for industry experience (0.0 to 1.0)")

    @model_validator(mode="after")
    def validate_weights_sum(self):
        total = round(self.education + self.publication + self.academic_experience + self.industry_experience, 4)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Scoring weights must sum to 1.0 (or 100%). Current sum: {total * 100}%")
        return self

class CreateSessionRequest(BaseModel):
    job_title: str = Field(..., json_schema_extra={"example": "Assistant Professor - Computer Science"})
    job_description: Optional[str] = Field(default="", json_schema_extra={"example": "Faculty recruitment for CS department"})
    required_degree: str = Field(..., json_schema_extra={"example": "PhD"})
    required_specialization: str = Field(..., json_schema_extra={"example": "Computer Science"})
    minimum_experience: float = Field(default=3.0, ge=0.0, json_schema_extra={"example": 3.0})
    minimum_publications: int = Field(default=5, ge=0, json_schema_extra={"example": 5})
    publication_window_years: int = Field(default=5, ge=1, json_schema_extra={"example": 5})
    top_n: int = Field(default=10, ge=1, json_schema_extra={"example": 10})
    scoring_weights: Optional[ScoringWeights] = Field(default_factory=ScoringWeights)

class SessionResponse(BaseModel):
    session_id: str
    job_title: str
    job_description: Optional[str] = ""
    required_degree: str
    required_specialization: str
    minimum_experience: float
    minimum_publications: int
    publication_window_years: int
    top_n: int
    scoring_weights: ScoringWeights
    processing_status: str  # CREATED, UPLOADED, PROCESSING, COMPLETED, FAILED
    current_stage: Optional[str] = "INITIAL"
    total_candidates: int = 0
    processed_candidates: int = 0
    failed_candidates: int = 0
    shortlisted_candidates: int = 0
    created_at: str
    completed_at: Optional[str] = None
