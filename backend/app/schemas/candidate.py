import re
from typing import Optional, List, Dict, Any, Union
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

def is_secondary_education(degree: Optional[str] = None, qual: Optional[str] = None) -> bool:
    """Detect if an education record represents 10th or 12th secondary schooling."""
    text = f"{degree or ''} {qual or ''}".lower().strip()
    if not text:
        return False

    # Check 10th patterns
    is_10th = any(k in text for k in (
        "10th", "10 th", "tenth", "class 10", "class x", "grade 10", "standard 10",
        "ssc", "sslc", "matric", "matriculation", "high school"
    )) or bool(re.search(r"\b(secondary school|secondary examination|secondary education|secondary cert)\b", text))

    # Check 12th patterns
    is_12th = any(k in text for k in (
        "12th", "12 th", "twelfth", "class 12", "class xii", "grade 12", "standard 12",
        "hsc", "higher secondary", "senior secondary", "intermediate", "inter ", "inter-",
        "+2", "plus two", "puc", "pre-university", "pre university", "isc"
    )) or bool(re.search(r"\b(mec|mpc|bipc)\b", text))

    if not (is_10th or is_12th):
        # Standalone secondary or inter check
        if re.search(r"\b(secondary|inter)\b", text):
            is_10th = True

    if not (is_10th or is_12th):
        return False

    # Guard: If candidate has a university degree in secondary education (e.g. B.Ed / M.Ed)
    if re.search(r"\b(bachelor|b\.ed|master|m\.ed|phd|ph\.d|doctor)\b", text):
        return False

    return True


def infer_qualification_type(degree: Optional[str], current_qual: Optional[str]) -> str:
    """
    Infer clean qualification type:
    - Postdoctoral / Post Doc -> 'Post Doctoral'
    - PhD / Doctorate -> 'PhD'
    - Master's / M.Sc / M.Tech / MBA / M.E. -> 'PG'
    - Bachelor's / B.Sc / B.Tech / B.E. -> 'UG'
    - 12th / HSC / Higher Secondary -> 'Other'
    - 10th / SSC / Secondary -> 'Other'
    """
    deg_lower = (degree or "").lower().strip()
    qual_lower = (current_qual or "").lower().strip()

    # 1. Postdoctoral (CRITICAL: Must be checked BEFORE PhD / Doctorate so 'Post Doctoral' never becomes 'PhD')
    if any(k in deg_lower for k in ("postdoc", "post-doc", "post doctoral", "post-doctoral", "pdf", "post doctorate")) or \
       any(k in qual_lower for k in ("postdoc", "post-doc", "post doctoral", "post-doctoral", "pdf", "post doctorate")):
        return "Post Doctoral"

    # 2. 10th and 12th secondary schooling -> 'Other'
    if is_secondary_education(deg_lower, qual_lower):
        return "Other"

    # 3. PhD / Doctorate
    if "phd" in qual_lower or "ph.d" in qual_lower or ("doctor" in qual_lower and "post" not in qual_lower):
        return "PhD"
    if "phd" in deg_lower or "ph.d" in deg_lower or ("doctor" in deg_lower and "post" not in deg_lower) or "d.phil" in deg_lower:
        return "PhD"

    # 4. PG (Master's)
    if qual_lower in ("pg", "post graduate", "postgraduate", "masters", "master"):
        return "PG"
    if any(term in deg_lower for term in (
        "master", "m.tech", "mtech", "m.sc", "msc", "mca", "mba", "m.phil", "mphil", "pg diploma", "post graduate"
    )) or bool(re.search(r"\b(m\.?e|m\.?s)\b", deg_lower)):
        return "PG"

    # 5. UG (Bachelor's)
    if qual_lower in ("ug", "under graduate", "undergraduate", "bachelors", "bachelor"):
        return "UG"
    if any(term in deg_lower for term in (
        "bachelor", "b.tech", "btech", "b.sc", "bsc", "bca", "bba", "b.com", "bcom", "b.a"
    )) or bool(re.search(r"\b(b\.?e|b\.?s|ba)\b", deg_lower)):
        return "UG"

    # 6. Current qualification if recognized
    if current_qual and current_qual in ("PhD", "Post Doctoral", "PG", "UG", "Other"):
        return current_qual

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
    qualification_type: Optional[str] = Field(default="Other", description="UG, PG, PhD, Post Doctoral, Other")
    degree: Optional[str] = None
    stream: Optional[str] = None
    university: Optional[str] = None
    year: Optional[str] = None
    cgpa: Optional[str] = None
    institution_tier: Optional[str] = Field(default="Tier 3", description="Tier 1, Tier 2, Tier 3 or null")
    institution_score: Optional[float] = Field(default=0.33, description="1.00 for Tier 1, 0.66 for Tier 2, 0.33 for Tier 3 or null")

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
        if s.lower() in ("pdf", "postdoc", "post-doc", "post doctoral", "postdoctoral"):
            return "Post Doctoral"
        if s in ("PhD", "Post Doctoral", "PG", "UG", "Other"):
            return s
        return s

    @model_validator(mode='after')
    def auto_infer_qualification_and_scores(self):
        cleaned_qual = sanitize_string_value(self.qualification_type)
        self.qualification_type = infer_qualification_type(self.degree, cleaned_qual)

        # 10th and 12th education must NOT receive institution tier or institution score
        if is_secondary_education(self.degree, self.qualification_type):
            self.institution_tier = None
            self.institution_score = None

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

    @field_validator('publication_name', 'published_at', mode='before')
    @classmethod
    def clean_strings(cls, v):
        return sanitize_string_value(v)

    @field_validator('venue_name', mode='before')
    @classmethod
    def clean_venue_name(cls, v):
        cleaned = sanitize_string_value(v)
        if not cleaned:
            return None
        # Year e.g. 2023 must never become venue_name
        import re
        if re.fullmatch(r"(19|20)\d{2}", cleaned.strip()):
            return None
        return cleaned

    @field_validator('publication_type', mode='before')
    @classmethod
    def clean_pub_type(cls, v):
        cleaned = sanitize_string_value(v)
        if not cleaned:
            return "other"
        s = cleaned.lower().strip()
        if "journal" in s:
            return "journal"
        elif "conf" in s or "proceedings" in s or "symposium" in s or "workshop" in s:
            return "conference"
        elif "book chapter" in s or "chapter" in s:
            return "book_chapter"
        elif "book" in s:
            return "book"
        elif "patent" in s:
            return "patent"
        elif s in ("journal", "conference", "book", "book_chapter", "patent", "other"):
            return s
        return "other"

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

    @model_validator(mode='after')
    def infer_and_clean_pub(self):
        import re
        # If publication_year is missing, infer from published_at
        if self.publication_year is None and self.published_at:
            m = re.search(r"\b(19|20)\d{2}\b", str(self.published_at))
            if m:
                self.publication_year = int(m.group(0))

        # Clean publication_name of leading numberings/prefixes like '1. ', 'Paper Title: ', etc.
        if self.publication_name:
            p = self.publication_name.strip()
            p = re.sub(r'^(?:\[\d+\]|\d+[\.\)]|\•|\-|\*)\s*', '', p)
            p = re.sub(r'^(?:Paper\s*Title\s*[:“"\'\s]+|Title\s*[:“"\'\s]+)', '', p, flags=re.IGNORECASE)
            p = p.strip(' "\'“”.')
            self.publication_name = p or None
        return self

# ---------------------------------------------------------
# Unified Experience Item Schema
# ---------------------------------------------------------
class ExperienceItem(BaseModel):
    experience_type: str = Field(default="professional", description="academic | professional")
    institution: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: float = Field(default=0.0, ge=0.0)
    description: Optional[str] = None

    # Harmonized aliases for backward compatibility
    company_name: Optional[str] = None
    organization: Optional[str] = None
    job_title: Optional[str] = None
    is_current: bool = False
    institution_tier: Optional[str] = "Tier 3"
    institution_score: float = 0.33

    @model_validator(mode='before')
    @classmethod
    def harmonize_fields(cls, data: Any):
        if isinstance(data, dict):
            r = data.get("role") or data.get("job_title") or data.get("designation")
            if r:
                data["role"] = r
                data["job_title"] = r
            inst = data.get("institution") or data.get("company_name") or data.get("company") or data.get("organization")
            if inst:
                data["institution"] = inst
                data["company_name"] = inst
                data["organization"] = inst
            
            exp_t = str(data.get("experience_type") or "").lower().strip()
            if any(k in exp_t for k in ("acad", "teach", "faculty", "fellow", "scholar", "lecturer", "professor")):
                data["experience_type"] = "academic"
            else:
                data["experience_type"] = "professional"
        return data

    @field_validator('institution', 'role', 'job_title', 'company_name', 'organization', 'start_date', 'end_date', 'description', mode='before')
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
# Academic Experience Item Schema
# ---------------------------------------------------------
class AcademicExperienceItem(BaseModel):
    experience_type: str = "academic"
    institution: Optional[str] = None
    role: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: float = Field(default=0.0, ge=0.0)
    description: Optional[str] = None
    is_current: bool = False
    is_internship: bool = False
    employment_type: Optional[str] = "full_time"
    institution_tier: Optional[str] = Field(default="Tier 3")
    institution_score: float = Field(default=0.33)

    @model_validator(mode='before')
    @classmethod
    def harmonize_fields(cls, data: Any):
        if isinstance(data, dict):
            r = data.get("role") or data.get("job_title") or data.get("designation")
            if r:
                data["role"] = r
                data["job_title"] = r
            inst = data.get("institution") or data.get("company_name") or data.get("company") or data.get("organization")
            if inst:
                data["institution"] = inst
                data["company_name"] = inst
        return data

    @field_validator('institution', 'role', 'job_title', 'company_name', 'start_date', 'end_date', 'description', mode='before')
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
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: float = Field(default=0.0, ge=0.0)
    location: Optional[str] = None
    description: Optional[str] = None
    is_current: bool = False
    is_internship: bool = False
    employment_type: Optional[str] = "full_time"

    @model_validator(mode='before')
    @classmethod
    def harmonize_fields(cls, data: Any):
        if isinstance(data, dict):
            r = data.get("role") or data.get("job_title") or data.get("designation")
            if r:
                data["role"] = r
                data["job_title"] = r
            org = data.get("organization") or data.get("company_name") or data.get("company") or data.get("institution")
            if org:
                data["organization"] = org
                data["company_name"] = org
        return data

    @field_validator('organization', 'role', 'job_title', 'company_name', 'location', 'start_date', 'end_date', 'description', mode='before')
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
    academic: List[Union[ExperienceItem, AcademicExperienceItem]] = Field(default_factory=list)
    professional: List[Union[ExperienceItem, IndustryExperienceItem]] = Field(default_factory=list)
    industry: Optional[List[Union[ExperienceItem, IndustryExperienceItem]]] = Field(default_factory=list)
    explicitly_mentioned_years: Optional[float] = None
    explicit_experience_text: Optional[str] = None
    calculated_total_years: Optional[float] = None
    calculation_basis: Optional[str] = "not_specified"
    experience_status: Optional[str] = "available"
    discrepancy_note: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def harmonize_professional_and_industry(cls, data: Any):
        if isinstance(data, dict):
            prof = data.get("professional")
            ind = data.get("industry")
            if prof is not None and ind is None:
                data["industry"] = prof
            elif ind is not None and prof is None:
                data["professional"] = ind
        return data

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
    experience: Union[ExperienceContainer, Dict[str, Any], List[ExperienceItem]] = Field(default_factory=dict)
    total_experience: Optional[float] = 0.0
    shortlisting: ShortlistingEvaluation = Field(default_factory=ShortlistingEvaluation)

class LLMExtractionRaw(BaseModel):
    personal_information: Optional[PersonalInformation] = Field(default_factory=PersonalInformation)
    education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    publications: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    experience: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(default_factory=dict)
    total_experience: Optional[float] = 0.0


