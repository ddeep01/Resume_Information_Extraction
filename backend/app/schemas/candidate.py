from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

def sanitize_string_value(v: Any) -> Optional[str]:
    """Sanitize string values: convert 'null', 'None', 'N/A', '', and prompt artifacts to None."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("null", "none", "n/a", "na", "undefined", ""):
        return None
    # Filter prompt option strings containing '|'
    if "|" in s and any(k in s for k in ("PhD", "M.Tech", "B.Tech", "Tier", "UG", "PG")):
        return None
    return s

def infer_qualification_type(degree: Optional[str], current_qual: Optional[str]) -> str:
    """Infer clean qualification type (PhD, PG, UG, PDF, JRF, Other) from degree text."""
    if current_qual and current_qual in ("PhD", "PG", "UG", "PDF", "JRF"):
        return current_qual
    
    if not degree:
        return "Other"
    
    deg_lower = degree.lower()
    if "doctor" in deg_lower or "phd" in deg_lower or "ph.d" in deg_lower:
        return "PhD"
    elif any(term in deg_lower for term in ("master", "m.tech", "mtech", "m.s", "ms", "m.sc", "msc", "mca", "mba", "m.e", "me")):
        return "PG"
    elif any(term in deg_lower for term in ("bachelor", "b.tech", "btech", "b.s", "bs", "b.sc", "bsc", "b.e", "be", "bca")):
        return "UG"
    elif "postdoc" in deg_lower or "post-doc" in deg_lower or "pdf" in deg_lower:
        return "PDF"
    elif "jrf" in deg_lower or "junior research fellow" in deg_lower:
        return "JRF"
    return "Other"

# ---------------------------------------------------------
# Personal Information Schema
# ---------------------------------------------------------
class PersonalInformation(BaseModel):
    full_name: Optional[str] = None
    current_designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator('full_name', 'current_designation', 'email', 'phone', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

# ---------------------------------------------------------
# Education Item Schema
# ---------------------------------------------------------
class EducationItem(BaseModel):
    qualification_type: Optional[str] = Field(default="Other", description="UG, PG, PhD, PDF, JRF, Other")
    degree: Optional[str] = None
    stream: Optional[str] = None
    university: Optional[str] = None
    year: Optional[str] = None
    cgpa: Optional[str] = None
    institution_tier: Optional[str] = Field(default="Tier 3", description="Tier 1, Tier 2, Tier 3")
    institution_score: float = Field(default=0.33, description="1.00 for Tier 1, 0.66 for Tier 2, 0.33 for Tier 3")

    @field_validator('degree', 'stream', 'university', 'year', 'cgpa', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

    @field_validator('qualification_type', mode='before')
    @classmethod
    def clean_qualification_type(cls, v):
        cleaned = sanitize_string_value(v)
        if not cleaned:
            return "Other"
        s = cleaned.strip()
        if s in ("PhD", "PG", "UG", "PDF", "JRF", "Other"):
            return s
        return s

    @model_validator(mode='after')
    def auto_infer_qualification(self):
        cleaned_qual = sanitize_string_value(self.qualification_type)
        self.qualification_type = infer_qualification_type(self.degree, cleaned_qual)
        return self

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

    @field_validator('publication_name', 'venue_name', 'published_at', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

    @field_validator('publication_year', mode='before')
    @classmethod
    def clean_year(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        if not s.isdigit():
            return None
        try:
            yr = int(s)
            return yr if 1950 <= yr <= 2030 else None
        except (ValueError, TypeError):
            return None

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

    @field_validator('institution', 'role', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

    @field_validator('duration_years', mode='before')
    @classmethod
    def sanitize_duration(cls, v):
        if v is None:
            return 0.0
        try:
            val = float(v)
            return max(0.0, val)
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

    @field_validator('organization', 'role', 'location', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

    @field_validator('duration_years', mode='before')
    @classmethod
    def sanitize_duration(cls, v):
        if v is None:
            return 0.0
        try:
            val = float(v)
            return max(0.0, val)
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
    education_score: float = 0.0
    publication_score: float = 0.0
    academic_experience_score: float = 0.0
    industry_experience_score: float = 0.0
    final_score: float = 0.0
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

class LLMExtractionRaw(BaseModel):
    personal_information: Optional[PersonalInformation] = Field(default_factory=PersonalInformation)
    education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    publications: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = Field(default_factory=dict)

