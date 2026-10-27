import pytest
from typing import Dict, Any, List

from backend.app.schemas.candidate import (
    EducationItem,
    is_secondary_education,
    infer_qualification_type,
    CandidateSchema,
    LLMExtractionRaw
)
from backend.app.shortlisting.scoring import calculate_education_score, calculate_final_score
from backend.app.shortlisting.degree_matcher import normalize_degree_name, matches_required_degree
from backend.app.shortlisting.eligibility import evaluate_candidate_eligibility
from backend.app.llm.extraction import LLMExtractor
from backend.app.llm.merger import HierarchicalMerger
from backend.app.llm.base import LLMProvider


# ==============================================================================
# 1. Qualification Type Inference & Level Distinctions
# ==============================================================================

def test_phd_qualification_classification():
    """Verify PhD / Doctorate degrees map strictly to 'PhD'."""
    assert infer_qualification_type("Ph.D. in Computer Science", "PhD") == "PhD"
    assert infer_qualification_type("Doctor of Philosophy", None) == "PhD"
    assert infer_qualification_type("PhD", None) == "PhD"
    assert infer_qualification_type("D.Phil in Artificial Intelligence", None) == "PhD"
    assert infer_qualification_type("Doctorate in Electrical Engineering", None) == "PhD"


def test_postdoctoral_distinction_critical():
    """CRITICAL TEST: Verify Post Doctoral / Postdoc is NEVER classified as PhD."""
    # Post Doctoral Researcher — Tufts University must NOT become PhD
    assert infer_qualification_type("Post Doctoral Researcher — Tufts University", "PhD") == "Post Doctoral"
    assert infer_qualification_type("Post Doctoral Researcher", None) == "Post Doctoral"
    assert infer_qualification_type("Post Doctoral Fellow", None) == "Post Doctoral"
    assert infer_qualification_type("Postdoc Research Fellow", None) == "Post Doctoral"
    assert infer_qualification_type("Post-Doctoral Training", None) == "Post Doctoral"
    assert infer_qualification_type("PDF", None) == "Post Doctoral"
    assert infer_qualification_type("Post Doctorate Scholar", None) == "Post Doctoral"
    assert infer_qualification_type("Senior Postdoc", None) == "Post Doctoral"


def test_pg_qualification_classification():
    """Verify Master's degrees map to 'PG'."""
    assert infer_qualification_type("M.Tech Computer Science", "PG") == "PG"
    assert infer_qualification_type("M.E. in Electronics", None) == "PG"
    assert infer_qualification_type("M.Sc. in Physics", None) == "PG"
    assert infer_qualification_type("M.S. Computer Science", None) == "PG"
    assert infer_qualification_type("Master of Computer Applications (MCA)", None) == "PG"
    assert infer_qualification_type("Master of Business Administration (MBA)", None) == "PG"
    assert infer_qualification_type("M.Phil in Management", None) == "PG"


def test_ug_qualification_classification():
    """Verify Bachelor's degrees map to 'UG'."""
    assert infer_qualification_type("B.Tech in Information Technology", "UG") == "UG"
    assert infer_qualification_type("B.E. Computer Engineering", None) == "UG"
    assert infer_qualification_type("B.Sc. Mathematics", None) == "UG"
    assert infer_qualification_type("B.S. in Electrical Engineering", None) == "UG"
    assert infer_qualification_type("BCA", None) == "UG"
    assert infer_qualification_type("BBA", None) == "UG"
    assert infer_qualification_type("B.Com", None) == "UG"
    assert infer_qualification_type("B.A. Economics", None) == "UG"


def test_secondary_12th_qualification_classification():
    """Verify 12th / HSC / Intermediate map to 'Other'."""
    assert infer_qualification_type("12th Standard", "Other") == "Other"
    assert infer_qualification_type("Higher Secondary Certificate (HSC)", None) == "Other"
    assert infer_qualification_type("Class XII (CBSE)", None) == "Other"
    assert infer_qualification_type("Senior Secondary Examination", None) == "Other"
    assert infer_qualification_type("Intermediate (MEC)", None) == "Other"
    assert infer_qualification_type("Inter MPC", None) == "Other"
    assert infer_qualification_type("+2 Higher Secondary", None) == "Other"
    assert infer_qualification_type("Pre-University Course (PUC)", None) == "Other"
    assert infer_qualification_type("ISC (Class 12)", None) == "Other"


def test_secondary_10th_qualification_classification():
    """Verify 10th / SSC / Matriculation map to 'Other'."""
    assert infer_qualification_type("10th Standard", "Other") == "Other"
    assert infer_qualification_type("Secondary School Certificate (SSC)", None) == "Other"
    assert infer_qualification_type("Class X", None) == "Other"
    assert infer_qualification_type("Matriculation", None) == "Other"
    assert infer_qualification_type("SSLC", None) == "Other"
    assert infer_qualification_type("High School Examination", None) == "Other"
    assert infer_qualification_type("Secondary Examination", None) == "Other"


# ==============================================================================
# 2. is_secondary_education Detection Accuracy
# ==============================================================================

def test_is_secondary_education_patterns():
    """Verify is_secondary_education correctly identifies 10th/12th while preserving higher education."""
    # 10th
    assert is_secondary_education("10th Standard") is True
    assert is_secondary_education("Class 10") is True
    assert is_secondary_education("Class X") is True
    assert is_secondary_education("SSC") is True
    assert is_secondary_education("Matric") is True
    assert is_secondary_education("Matriculation") is True
    assert is_secondary_education("High School") is True
    assert is_secondary_education("Secondary School Certificate") is True

    # 12th
    assert is_secondary_education("12th Standard") is True
    assert is_secondary_education("Class 12") is True
    assert is_secondary_education("Class XII") is True
    assert is_secondary_education("HSC") is True
    assert is_secondary_education("Higher Secondary") is True
    assert is_secondary_education("Senior Secondary") is True
    assert is_secondary_education("Intermediate (M.E.C)") is True
    assert is_secondary_education("+2") is True
    assert is_secondary_education("PUC") is True
    assert is_secondary_education("ISC") is True

    # Higher education MUST NOT be flagged as secondary
    assert is_secondary_education("Ph.D. in Computer Science") is False
    assert is_secondary_education("Post Doctoral Researcher") is False
    assert is_secondary_education("M.Tech Software Engineering") is False
    assert is_secondary_education("Master of Science") is False
    assert is_secondary_education("B.Tech Computer Science") is False
    assert is_secondary_education("Bachelor of Technology") is False
    assert is_secondary_education("B.Sc Mathematics") is False
    assert is_secondary_education("MBA") is False


# ==============================================================================
# 3. 10th and 12th Institution Tier & Score Suppression (Strictly null)
# ==============================================================================

def test_education_item_nulls_scores_for_10th_and_12th():
    """Verify EducationItem schema sets institution_tier and institution_score to None for 10th/12th."""
    # 10th record
    edu_10th = EducationItem(
        qualification_type="Other",
        degree="10th Standard (SSC)",
        university="CBSE",
        year="2012",
        cgpa="9.2 CGPA",
        institution_tier="Tier 3",  # Even if passed explicitly
        institution_score=0.33       # Even if passed explicitly
    )
    dumped_10th = edu_10th.model_dump()
    assert dumped_10th["qualification_type"] == "Other"
    assert dumped_10th["institution_tier"] is None
    assert dumped_10th["institution_score"] is None

    # 12th record
    edu_12th = EducationItem(
        qualification_type="Other",
        degree="Intermediate (M.E.C)",
        university="State Board of Intermediate Education",
        year="2014",
        cgpa="88%",
        institution_tier="Tier 2",
        institution_score=0.66
    )
    dumped_12th = edu_12th.model_dump()
    assert dumped_12th["qualification_type"] == "Other"
    assert dumped_12th["institution_tier"] is None
    assert dumped_12th["institution_score"] is None


def test_education_item_preserves_scores_for_higher_education():
    """Verify higher education records (UG, PG, PhD, Post Doctoral) preserve institution tier & score."""
    edu_ug = EducationItem(
        qualification_type="UG",
        degree="B.Tech in Computer Science",
        university="IIT Delhi",
        year="2018",
        cgpa="8.5 CGPA",
        institution_tier="Tier 1",
        institution_score=1.0
    )
    dumped_ug = edu_ug.model_dump()
    assert dumped_ug["qualification_type"] == "UG"
    assert dumped_ug["institution_tier"] == "Tier 1"
    assert dumped_ug["institution_score"] == 1.0

    edu_postdoc = EducationItem(
        qualification_type="Post Doctoral",
        degree="Post Doctoral Researcher — Tufts University",
        university="Tufts University",
        year="2024",
        institution_tier="Tier 1",
        institution_score=1.0
    )
    dumped_postdoc = edu_postdoc.model_dump()
    assert dumped_postdoc["qualification_type"] == "Post Doctoral"
    assert dumped_postdoc["institution_tier"] == "Tier 1"
    assert dumped_postdoc["institution_score"] == 1.0


# ==============================================================================
# 4. Education Scoring Compatibility: 10th/12th Must NOT Affect Score
# ==============================================================================

def test_education_scoring_ignores_10th_and_12th():
    """Verify 10th and 12th qualifications do NOT contribute to or dilute education score."""
    # Candidate with only UG Tier 1 (1.0)
    cand_ug_only = [
        {"degree": "B.Tech", "qualification_type": "UG", "institution_score": 1.0, "institution_tier": "Tier 1"}
    ]
    score_ug_only = calculate_education_score(cand_ug_only)
    assert score_ug_only == 1.0

    # Same candidate with 10th and 12th added
    cand_with_secondary = [
        {"degree": "B.Tech", "qualification_type": "UG", "institution_score": 1.0, "institution_tier": "Tier 1"},
        {"degree": "Intermediate / 12th", "qualification_type": "Other", "institution_score": None, "institution_tier": None},
        {"degree": "SSC / 10th", "qualification_type": "Other", "institution_score": None, "institution_tier": None}
    ]
    score_with_secondary = calculate_education_score(cand_with_secondary)
    # The score MUST remain 1.0; 10th and 12th must not dilute it
    assert score_with_secondary == 1.0


def test_education_scoring_with_postdoc_phd_pg_ug():
    """Verify composite education score with Post Doctoral, PhD, PG, UG, 12th, 10th."""
    education_list = [
        {"degree": "Post Doctoral Fellow", "qualification_type": "Post Doctoral", "institution_score": 1.0, "institution_tier": "Tier 1"},
        {"degree": "Ph.D. Computer Science", "qualification_type": "PhD", "institution_score": 1.0, "institution_tier": "Tier 1"},
        {"degree": "M.Tech AI", "qualification_type": "PG", "institution_score": 0.66, "institution_tier": "Tier 2"},
        {"degree": "B.Tech IT", "qualification_type": "UG", "institution_score": 0.33, "institution_tier": "Tier 3"},
        {"degree": "Class XII", "qualification_type": "Other", "institution_score": None, "institution_tier": None},
        {"degree": "Class X", "qualification_type": "Other", "institution_score": None, "institution_tier": None}
    ]
    # Weights: Postdoc/PhD = 0.50, PG = 0.30, UG = 0.20
    # Weighted calculation: (1.0 * 0.5) + (1.0 * 0.5) + (0.66 * 0.3) + (0.33 * 0.2)
    # 0.5 + 0.5 + 0.198 + 0.066 = 1.264 / (0.5 + 0.5 + 0.3 + 0.2 = 1.5) = 0.8427
    score = calculate_education_score(education_list)
    assert score > 0.8
    assert score < 0.9


def test_education_scoring_candidate_with_only_secondary():
    """Verify candidate with only secondary education gets safe default score and does not crash."""
    education_list = [
        {"degree": "12th Standard", "qualification_type": "Other", "institution_score": None, "institution_tier": None},
        {"degree": "10th Standard", "qualification_type": "Other", "institution_score": None, "institution_tier": None}
    ]
    score = calculate_education_score(education_list)
    # Fallback score is 0.33
    assert score == 0.33


# ==============================================================================
# 5. Shortlisting & Eligibility: 10th/12th Do NOT Cause False Eligibility
# ==============================================================================

def test_degree_matching_and_shortlisting_with_10th_12th():
    """Verify 10th/12th do not falsely meet higher degree requirements."""
    cand_secondary_only = {
        "education": [
            {"degree": "Higher Secondary / 12th", "qualification_type": "Other", "institution_tier": None, "institution_score": None},
            {"degree": "Secondary / 10th", "qualification_type": "Other", "institution_tier": None, "institution_score": None}
        ],
        "experience": {"academic": [], "professional": []},
        "publications": []
    }

    # B.Tech requirement: candidate with only 10th/12th must FAIL
    eligible, reasons, _, _ = evaluate_candidate_eligibility(
        candidate_data=cand_secondary_only,
        required_degree="B.Tech",
        required_specialization="any",
        minimum_experience=0.0,
        minimum_publications=0,
        publication_window_years=5
    )
    assert eligible is False
    assert any("Required degree 'B.Tech' not found" in r for r in reasons)


def test_postdoctoral_meets_or_exceeds_phd_requirement():
    """Verify Post Doctoral candidate meets PhD degree requirement in shortlisting."""
    cand_postdoc = {
        "education": [
            {"degree": "Post Doctoral Researcher", "qualification_type": "Post Doctoral", "stream": "Machine Learning", "institution_tier": "Tier 1", "institution_score": 1.0},
            {"degree": "Ph.D. in Computer Science", "qualification_type": "PhD", "stream": "Computer Science", "institution_tier": "Tier 1", "institution_score": 1.0}
        ],
        "experience": {"academic": [], "professional": []},
        "publications": []
    }

    eligible, reasons, _, _ = evaluate_candidate_eligibility(
        candidate_data=cand_postdoc,
        required_degree="PhD",
        required_specialization="Computer Science",
        minimum_experience=0.0,
        minimum_publications=0,
        publication_window_years=5
    )
    assert eligible is True
    assert any("meets or exceeds" in r for r in reasons)


# ==============================================================================
# 6. Separate Education Records & Deduplication in Merger
# ==============================================================================

class DummyProvider(LLMProvider):
    def generate(self, prompt: str, system: str = "") -> str:
        return "{}"


def test_separate_education_records_not_merged_by_merger():
    """Verify merger preserves separate degrees and does not combine distinct qualifications."""
    merger = HierarchicalMerger(provider=DummyProvider())

    json_a = {
        "education": [
            {"qualification_type": "UG", "degree": "B.Tech", "university": "IIT Bombay", "year": "2018"},
            {"qualification_type": "Other", "degree": "12th Standard", "university": "CBSE", "year": "2014"}
        ]
    }
    json_b = {
        "education": [
            {"qualification_type": "PG", "degree": "M.Tech", "university": "IIT Bombay", "year": "2020"},
            {"qualification_type": "Other", "degree": "10th Standard", "university": "CBSE", "year": "2012"}
        ]
    }

    merged = merger.python_deterministic_merge(json_a, json_b)
    edu_records = merged.get("education", [])
    # Distinct degrees at same university (B.Tech at IIT Bombay vs M.Tech at IIT Bombay) must remain separate
    # Distinct secondary education (12th at CBSE vs 10th at CBSE) must remain separate
    assert len(edu_records) == 4
    degrees = [e["degree"] for e in edu_records]
    assert "B.Tech" in degrees
    assert "M.Tech" in degrees
    assert "12th Standard" in degrees
    assert "10th Standard" in degrees


def test_complementary_education_records_merged_properly():
    """Verify complementary information for the SAME degree across chunks is merged."""
    merger = HierarchicalMerger(provider=DummyProvider())

    # Chunk 1 had degree and university
    json_a = {
        "education": [
            {"qualification_type": "UG", "degree": "B.Tech", "university": "Anna University", "year": None, "cgpa": None}
        ]
    }
    # Chunk 2 had same degree, university, but with year and CGPA
    json_b = {
        "education": [
            {"qualification_type": "UG", "degree": "B.Tech", "university": "Anna University", "year": "2021", "cgpa": "8.7 CGPA"}
        ]
    }

    merged = merger.python_deterministic_merge(json_a, json_b)
    edu_records = merged.get("education", [])
    assert len(edu_records) == 1
    assert edu_records[0]["degree"] == "B.Tech"
    assert edu_records[0]["year"] == "2021"
    assert edu_records[0]["cgpa"] == "8.7 CGPA"


# ==============================================================================
# 7. Strict Anti-Pollution: Dropping Non-Academic Items from Education
# ==============================================================================

def test_verify_and_clean_data_filters_non_academic_items():
    """Verify certifications, workshops, seminars, and projects are dropped from education."""
    extractor = LLMExtractor(provider=DummyProvider())

    raw_dict = {
        "education": [
            {"qualification_type": "UG", "degree": "B.Tech in Computer Science", "university": "Delhi University"},
            {"qualification_type": "Other", "degree": "AWS Certified Solutions Architect", "university": "Amazon"},
            {"qualification_type": "Other", "degree": "5-Day National Workshop on Deep Learning", "university": "IIT Madras"},
            {"qualification_type": "Other", "degree": "Faculty Development Program (FDP) on AI", "university": "NIT Trichy"},
            {"qualification_type": "Other", "degree": "Final Year Capstone Project", "university": "Delhi University"},
            {"qualification_type": "Other", "degree": "NPTEL Online Certification in Python", "university": "NPTEL"},
            {"qualification_type": "Post Doctoral", "degree": "Post Doctoral Researcher — Tufts University", "university": "Tufts University"},
            {"qualification_type": "Other", "degree": "10th Standard", "university": "CBSE"}
        ],
        "experience": {"academic": [], "professional": []},
        "publications": []
    }

    cleaned = extractor.verify_and_clean_data(raw_dict, raw_text="B.Tech in Computer Science at Delhi University 10th Standard CBSE Tufts University")
    cleaned_edu = cleaned.get("education", [])

    # The 3 genuine qualifications (B.Tech, Post Doctoral, 10th Standard) should be kept
    # The 5 non-academic items (AWS, Workshop, FDP, Capstone Project, NPTEL) must be dropped
    deg_names = [e["degree"] for e in cleaned_edu]
    assert "B.Tech in Computer Science" in deg_names
    assert "Post Doctoral Researcher — Tufts University" in deg_names
    assert "10th Standard" in deg_names

    assert not any("AWS Certified" in d for d in deg_names)
    assert not any("Workshop" in d for d in deg_names)
    assert not any("FDP" in d for d in deg_names)
    assert not any("Capstone Project" in d for d in deg_names)
    assert not any("NPTEL" in d for d in deg_names)

    # Verify 10th has null tier and null score
    item_10th = next(e for e in cleaned_edu if "10th" in e["degree"])
    assert item_10th["institution_tier"] is None
    assert item_10th["institution_score"] is None


# ==============================================================================
# 8. Missing and Unusual Data Handling (No Hallucination)
# ==============================================================================

def test_missing_year_and_cgpa_preserved_as_null():
    """Verify missing year and missing CGPA remain null without inventing data."""
    edu_item = EducationItem(
        qualification_type="UG",
        degree="B.Sc Computer Science",
        university="University of Mumbai",
        year=None,
        cgpa=None
    )
    dumped = edu_item.model_dump()
    assert dumped["year"] is None
    assert dumped["cgpa"] is None
    assert dumped["degree"] == "B.Sc Computer Science"
    assert dumped["university"] == "University of Mumbai"


def test_prompt_placeholder_leak_sanitization():
    """Verify prompt options like 'PhD | M.Tech...' are sanitized to null."""
    edu_item = EducationItem(
        qualification_type="UG",
        degree="B.Tech",
        stream="PhD | M.Tech | B.Tech",
        university="Name of College or University",
        year="2020"
    )
    dumped = edu_item.model_dump()
    assert dumped["stream"] is None
