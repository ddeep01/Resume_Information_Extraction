import pytest
from backend.app.config import settings
from backend.app.shortlisting.scoring import (
    calculate_academic_experience_score,
    calculate_industry_experience_score,
    calculate_final_score
)
from backend.app.schemas.candidate import sanitize_string_value
from backend.app.llm.experience_calculator import clean_and_calculate_experience_dict, is_unrelated_experience_item
from backend.app.llm.extraction import (
    extract_candidate_name_from_text,
    extract_education_from_section,
    extract_publications_from_text,
    LLMExtractor
)
from tests.test_adaptive_extraction import MockLLMProvider

def test_academic_experience_scoring_duration_and_tier():
    # 5 years at Tier 1 (1.0) -> (5/10)*0.4 + 1.0*0.6 = 0.2 + 0.6 = 0.8
    score = calculate_academic_experience_score([
        {"institution": "IIT Bombay", "duration_years": 5.0, "institution_score": 1.0}
    ])
    assert score == 0.80

    # 12 years (capped at 10) at Tier 2 (0.66) -> 1.0*0.4 + 0.66*0.6 = 0.4 + 0.396 = 0.796
    score_capped = calculate_academic_experience_score([
        {"institution": "State University", "duration_years": 12.0, "institution_score": 0.66}
    ])
    assert score_capped == 0.796

def test_industry_experience_scoring_duration_and_tier():
    # 4 years at Tier 1 (1.0) -> (4/8)*0.4 + 1.0*0.6 = 0.2 + 0.6 = 0.8
    score = calculate_industry_experience_score([
        {"company": "Google", "duration_years": 4.0, "institution_score": 1.0}
    ])
    assert score == 0.80

    # 10 years (capped at 8) at Tier 3 (0.33) -> 1.0*0.4 + 0.33*0.6 = 0.4 + 0.198 = 0.598
    score_capped = calculate_industry_experience_score([
        {"company": "Local Startup", "duration_years": 10.0, "institution_score": 0.33}
    ])
    assert score_capped == 0.598

def test_experience_scoring_multiple_organizations_average_tier():
    # Academic: 2 orgs (Tier 1: 1.0, Tier 2: 0.66) -> avg tier = 0.83, total 5 yrs -> 0.5*0.4 + 0.83*0.6 = 0.20 + 0.498 = 0.698
    score = calculate_academic_experience_score([
        {"institution": "IIT Delhi", "duration_years": 2.0, "institution_score": 1.0},
        {"institution": "NIT Trichy", "duration_years": 3.0, "institution_score": 0.66}
    ])
    expected_avg_tier = (1.0 + 0.66) / 2.0
    expected_score = round((5.0 / 10.0 * 0.4) + (expected_avg_tier * 0.6), 4)
    assert score == expected_score

    # Industry: 2 orgs (Tier 1: 1.0, Tier 3: 0.33) -> avg tier = 0.665, total 4 yrs -> 0.5*0.4 + 0.665*0.6 = 0.20 + 0.399 = 0.599
    ind_score = calculate_industry_experience_score([
        {"company": "Microsoft", "duration_years": 2.0, "institution_score": 1.0},
        {"company": "Tech Corp", "duration_years": 2.0, "institution_score": 0.33}
    ])
    expected_ind_avg = (1.0 + 0.33) / 2.0
    expected_ind_score = round((4.0 / 8.0 * 0.4) + (expected_ind_avg * 0.6), 4)
    assert ind_score == expected_ind_score

def test_experience_scoring_zero_when_no_relevant_experience():
    assert calculate_academic_experience_score([]) == 0.0
    assert calculate_academic_experience_score([{"institution": None, "role": None, "duration_years": 0.0}]) == 0.0
    assert calculate_industry_experience_score([]) == 0.0
    assert calculate_industry_experience_score([{"company": None, "role": None, "duration_years": 0.0}]) == 0.0

def test_resume_length_threshold_config():
    assert hasattr(settings, "MAX_RESUME_CHAR_LIMIT")
    assert settings.MAX_RESUME_CHAR_LIMIT == 25000

def test_schema_leak_sanitization():
    # Prompt leak " or John Doe"
    assert sanitize_string_value("Bhumika Shah or John Doe") == "Bhumika Shah"
    assert sanitize_string_value("John Doe") is None
    assert sanitize_string_value("email@example.com") is None
    assert sanitize_string_value("+91 9876543210") is None

    # Prompt leak "| null"
    assert sanitize_string_value("PhD | null | null") == "PhD"
    assert sanitize_string_value("null") is None
    assert sanitize_string_value("None") is None
    assert sanitize_string_value("N/A") is None

def test_section_validation_filters_skills_from_experience():
    # Tally Erp9 and software skills should not be treated as employment experience
    raw_exp = {
        "professional": [
            {"institution": "Rai University", "role": "Assistant Professor", "duration_years": 2.5},
            {"institution": "Tally Erp9", "role": None, "duration_years": 0.0},
            {"institution": "Python", "role": None, "duration_years": 0.0},
            {"institution": "null", "role": None, "duration_years": 0.0}
        ]
    }
    cleaned_dict, total_exp = clean_and_calculate_experience_dict(raw_exp)
    prof_items = cleaned_dict["professional"]
    inst_names = [it["institution"] for it in prof_items]
    assert "Rai University" in inst_names
    assert "Tally Erp9" not in inst_names
    assert "Python" not in inst_names
    assert "null" not in inst_names

def test_phd_education_rescue_from_text():
    sample_cv = """
    DR. MITESHKUMAR SOLANKI
    Assistant Professor
    Education
    2013-2021
    Doctor of Philosophy (PhD) in Single Crystal Growth and DFT
    Pandit Deendayal Energy University Gandhinagar, INDIA
    2010-2012
    Master of Science (M. Sc.) in Physics
    Saurashtra University Rajkot, INDIA
    Employment
    July. 2023 - till date Assistant Professor
    """
    edus = extract_education_from_section(sample_cv)
    qtypes = [e["qualification_type"] for e in edus]
    assert "PhD" in qtypes
    assert "PG" in qtypes
    phd_edu = [e for e in edus if e["qualification_type"] == "PhD"][0]
    assert "Pandit Deendayal Energy University" in phd_edu["university"]
    assert phd_edu["year"] == "2021"

def test_publications_rescue_from_text():
    sample_pubs = """
    Rakesh Ranjan
    Research Publications
    Journals/ Conferences
    1. Rakesh. Ranjan, A. Bhattacharya, H.B. Mishra and S. Mukhopadhyay, "A Gradient Ascent Based Low Complexity Rate Maximization Algorithm for Intelligent Reflecting Surface-Aided OFDM Systems" IEEE Communications Letters, vol. 27, no. 8, pp. 2083-2087, Aug. 2023.
    2. Rakesh. Ranjan, A. Bhattacharya, H. B. Mishra and S. Mukhopadhyay, "A Low-Complexity Phase Shift Optimization to Achieve Security in IRS-Assisted MISO Systems," IEEE National Conference on Communications (NCC) 2024, IIT-Madras.
    """
    pubs = extract_publications_from_text(sample_pubs)
    assert len(pubs) == 2
    assert "A Gradient Ascent Based Low Complexity Rate Maximization" in pubs[0]["publication_name"]
    assert "IEEE Communications Letters" in pubs[0]["venue_name"]
    assert pubs[0]["publication_year"] == 2023
    assert pubs[1]["publication_year"] == 2024
