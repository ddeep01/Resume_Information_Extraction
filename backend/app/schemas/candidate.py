from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------
# Personal Information Schema
# ---------------------------------------------------------
class PersonalInformation(BaseModel):
    full_name: Optional[str] = None
    current_designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

# ---------------------------------------------------------
# Education Item Schema
# ---------------------------------------------------------
class EducationItem(BaseModel):
    qualification_type: Optional[str] = Field(default="Other", description="UG, PG, PhD, PDF, JRF")
    degree: Optional[str] = None
    stream: Optional[str] = None
    university: Optional[str] = None
    year: Optional[str] = None
    cgpa: Optional[str] = None
    institution_tier: Optional[str] = Field(default="Tier 3", description="Tier 1, Tier 2, Tier 3")
    institution_score: float = Field(default=0.33, description="1.00 for Tier 1, 0.66 for Tier 2, 0.33 for Tier 3")

# ---------------------------------------------------------
# Publication Item Schema
# ---------------------------------------------------------
class PublicationItem(BaseModel):
    publication_type: Optional[str] = Field(default="other", description="journal, conference, book, book_chapter, patent, other")
    publication_name: Optional[str] = None
    venue_name: Optional[str] = None
    published_at: Optional[str] = None
    publication_year: Optional[int] = None
    venue_tier: Optional[str] = Field(default="Tier 3", description="Tier 1, Tier 2, Tier 3")
    venue_score: float = Field(default=0.33, description="1.00 for Tier 1, 0.66 for Tier 2, 0.33 for Tier 3")
    in_publication_window: bool = Field(default=True, description="Whether published within required window")

# ---------------------------------------------------------
# Academic Experience Item Schema
# ---------------------------------------------------------
class AcademicExperienceItem(BaseModel):
    experience_type: str = "academic"
    institution: Optional[str] = None
    role: Optional[str] = None
    duration_years: float = Field(default=0.0, ge=0.0)
    institution_tier: Optional[str] = Field(default="Tier 3")
    institution_score: float = Field(default=0.33)

    @field_validator('duration_years', mode='before')
    @classmethod
    def sanitize_duration(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

# ---------------------------------------------------------
# Industry Experience Item Schema
# ---------------------------------------------------------
class IndustryExperienceItem(BaseModel):
    experience_type: str = "industry"
    organization: Optional[str] = None
    role: Optional[str] = None
    duration_years: float = Field(default=0.0, ge=0.0)
    location: Optional[str] = None

    @field_validator('duration_years', mode='before')
    @classmethod
    def sanitize_duration(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

# ---------------------------------------------------------
# Experience Container Schema
# ---------------------------------------------------------
class ExperienceContainer(BaseModel):
    academic: List[AcademicExperienceItem] = Field(default_factory=list)
    industry: List[IndustryExperienceItem] = Field(default_factory=list)

# ---------------------------------------------------------
# Shortlisting Evaluation Schema
# ---------------------------------------------------------
class ShortlistingEvaluation(BaseModel):
    eligible: bool = False
    shortlisted: bool = False
    education_score: float = 0.0  # 0.0 to 1.0
    publication_score: float = 0.0  # 0.0 to 1.0
    academic_experience_score: float = 0.0  # 0.0 to 1.0
    industry_experience_score: float = 0.0  # 0.0 to 1.0
    final_score: float = 0.0  # 0.0 to 100.0
    rank: Optional[int] = None
    reasons: List[str] = Field(default_factory=list)

# ---------------------------------------------------------
# Master Candidate Schema
# ---------------------------------------------------------
class CandidateSchema(BaseModel):
    candidate_id: str
    source_file: str
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    education: List[EducationItem] = Field(default_factory=list)
    publications: List[PublicationItem] = Field(default_factory=list)
    experience: ExperienceContainer = Field(default_factory=ExperienceContainer)
    shortlisting: ShortlistingEvaluation = Field(default_factory=ShortlistingEvaluation)

# Schema for LLM Extraction Output Parsing
class LLMExtractionRaw(BaseModel):
    personal_information: Optional[PersonalInformation] = Field(default_factory=PersonalInformation)
    education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    publications: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = Field(default_factory=dict)
