"""
Test Suite for Resume Work Experience Extraction and Calculation.
Covers all 14 mandatory scenarios:
1. Candidate explicitly mentions 10 years of experience.
2. Candidate explicitly mentions 5.5 years of experience.
3. Candidate has employment history but no total experience mentioned.
4. Candidate has worked at three different companies.
5. Candidate has overlapping employment periods.
6. Candidate is currently employed (e.g. Present, Ongoing, Now).
7. Candidate uses different date formats (Jan 2018 - Dec 2020, 01/2018 - 12/2020, 2018 - 2020).
8. Candidate mentions employment in the professional summary.
9. Candidate mentions company and designation but no dates.
10. Candidate has internship experience only.
11. Candidate has freelance experience.
12. Candidate has employment gaps (gaps must not be counted).
13. Candidate has explicit experience that disagrees with calculated experience (discrepancy detected).
14. Candidate has no identifiable employment history (fresh graduate -> zero_experience).
"""

import pytest
from datetime import datetime
from backend.app.llm.experience_calculator import (
    calculate_and_enrich_experience,
    parse_date_to_decimal,
    merge_intervals,
    extract_explicit_experience_from_text,
    normalize_experience_item
)
from backend.app.schemas.candidate import (
    ExperienceContainer,
    AcademicExperienceItem,
    IndustryExperienceItem
)


# Fixed reference year/month for deterministic test calculations: 2026.0 (Jan 2026)
TEST_CURRENT_YEAR = 2026
TEST_CURRENT_MONTH = 1


def test_scenario_01_explicit_10_years():
    """Scenario 1: Candidate explicitly mentions 10 years of experience."""
    text = (
        "SARAH CONNOR\n"
        "Summary: Senior DevOps Architect with over 10 years of experience in enterprise cloud deployments.\n"
        "Education: B.Tech in CSE, 2014"
    )
    raw_exp = {
        "explicitly_mentioned_years": 10.0,
        "explicit_experience_text": "over 10 years of experience",
        "academic": [],
        "industry": []
    }
    enriched = calculate_and_enrich_experience(raw_exp, full_resume_text=text, current_year=TEST_CURRENT_YEAR)

    assert enriched["explicitly_mentioned_years"] == 10.0
    assert enriched["calculated_total_years"] == 10.0
    assert enriched["calculation_basis"] == "explicitly_stated"
    assert enriched["experience_status"] == "available"


def test_scenario_02_explicit_5_5_years():
    """Scenario 2: Candidate explicitly mentions 5.5 years of experience."""
    text = (
        "ALEX MERCER\n"
        "Professional Summary: Dedicated Full-Stack Engineer with 5.5 years of IT experience "
        "specializing in React, Python, and scalable microservices."
    )
    # Even if LLM omitted explicitly_mentioned_years in JSON, text regex extraction captures it
    enriched = calculate_and_enrich_experience({}, full_resume_text=text, current_year=TEST_CURRENT_YEAR)

    assert enriched["explicitly_mentioned_years"] == 5.5
    assert enriched["calculated_total_years"] == 5.5
    assert enriched["calculation_basis"] == "explicitly_stated"
    assert enriched["experience_status"] == "available"


def test_scenario_03_employment_history_no_explicit_total():
    """Scenario 3: Candidate has employment history but no total experience mentioned."""
    raw_exp = {
        "explicitly_mentioned_years": None,
        "industry": [
            {
                "company_name": "Tech Corp",
                "job_title": "Software Engineer",
                "start_date": "January 2018",
                "end_date": "December 2021"
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, full_resume_text="No explicit years stated.", current_year=TEST_CURRENT_YEAR)

    # Jan 2018 to Dec 2021 = ~4.0 years
    assert enriched["calculated_total_years"] >= 3.9
    assert enriched["calculation_basis"] == "calculated_from_history"
    assert enriched["experience_status"] == "available"


def test_scenario_04_three_different_companies():
    """Scenario 4: Candidate has worked at three different companies."""
    raw_exp = {
        "industry": [
            {
                "company_name": "Company Alpha",
                "job_title": "Junior Developer",
                "start_date": "January 2015",
                "end_date": "December 2017"  # 3 yrs
            },
            {
                "company_name": "Company Beta",
                "job_title": "Senior Developer",
                "start_date": "January 2018",
                "end_date": "December 2020"  # 3 yrs
            },
            {
                "company_name": "Company Gamma",
                "job_title": "Lead Architect",
                "start_date": "January 2021",
                "end_date": "December 2023"  # 3 yrs
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    # 3 + 3 + 3 = 9.0 years total across distinct companies
    assert enriched["calculated_total_years"] >= 8.9
    assert enriched["calculation_basis"] == "calculated_from_history"
    assert len(enriched["industry"]) == 3
    companies = [c["company_name"] for c in enriched["industry"]]
    assert companies == ["Company Alpha", "Company Beta", "Company Gamma"]


def test_scenario_05_overlapping_employment_periods():
    """Scenario 5: Candidate has overlapping employment periods. Overlap must NOT be double-counted."""
    raw_exp = {
        "industry": [
            {
                "company_name": "Alpha Corp",
                "job_title": "Software Engineer",
                "start_date": "January 2018",
                "end_date": "December 2020"  # 2018.0 to 2021.0 = 3 years
            },
            {
                "company_name": "Beta Consulting (Part-time / Overlap)",
                "job_title": "Consultant",
                "start_date": "January 2020",
                "end_date": "December 2022"  # 2020.0 to 2023.0 = 3 years
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    # Union interval is Jan 2018 to Dec 2022 = 5 years (not 3 + 3 = 6 years)
    assert enriched["calculated_total_years"] == pytest.approx(5.0, abs=0.2)
    assert enriched["calculation_basis"] == "calculated_from_history"


def test_scenario_06_currently_employed():
    """Scenario 6: Candidate is currently employed (Present, Current, Ongoing)."""
    raw_exp = {
        "industry": [
            {
                "company_name": "CloudNine Inc",
                "job_title": "Staff Engineer",
                "start_date": "January 2021",
                "end_date": "Present",
                "is_current": True
            }
        ]
    }
    # Current date: Jan 2026 -> Jan 2021 to Jan 2026 = 5.0 years
    enriched = calculate_and_enrich_experience(raw_exp, current_year=2026, current_month=1)

    assert enriched["calculated_total_years"] >= 5.0
    assert enriched["industry"][0]["is_current"] is True
    assert enriched["experience_status"] == "available"


def test_scenario_07_different_date_formats():
    """Scenario 7: Candidate uses different date representations."""
    # MM/YYYY
    d1_start = parse_date_to_decimal("01/2018", is_end_date=False)
    d1_end = parse_date_to_decimal("12/2020", is_end_date=True)
    assert d1_start == pytest.approx(2018.0, abs=0.05)
    assert d1_end == pytest.approx(2021.0, abs=0.05)

    # Jan 2018 - Dec 2020
    d2_start = parse_date_to_decimal("Jan 2018", is_end_date=False)
    d2_end = parse_date_to_decimal("December 2020", is_end_date=True)
    assert d2_start == pytest.approx(2018.0, abs=0.05)
    assert d2_end == pytest.approx(2021.0, abs=0.05)

    # YYYY - YYYY
    d3_start = parse_date_to_decimal("2018", is_end_date=False)
    d3_end = parse_date_to_decimal("2020", is_end_date=True)
    assert d3_start == 2018.0
    assert d3_end == 2021.0

    # Till Date / Ongoing / Now
    d4_end = parse_date_to_decimal("Till Date", is_end_date=True, current_year=2026, current_month=1)
    assert d4_end == pytest.approx(2026.08, abs=0.1)


def test_scenario_08_employment_in_professional_summary():
    """Scenario 8: Candidate mentions employment details in professional summary."""
    resume_text = (
        "PRIYA SHARMA\n"
        "Email: priya@example.com\n"
        "PROFESSIONAL SUMMARY\n"
        "Currently working as a Senior Developer at ABC Technologies since 2021 with over 8 years of professional experience in data engineering.\n"
        "SKILLS\n"
        "Python, SQL, PySpark, Airflow\n"
        "EDUCATION\n"
        "B.E. Computer Science, 2015"
    )
    years, text_found = extract_explicit_experience_from_text(resume_text)
    assert years == 8.0
    assert "8 years of professional experience" in text_found

    enriched = calculate_and_enrich_experience({}, full_resume_text=resume_text, current_year=TEST_CURRENT_YEAR)
    assert enriched["explicitly_mentioned_years"] == 8.0
    assert enriched["calculated_total_years"] == 8.0
    assert enriched["experience_status"] == "available"


def test_scenario_09_company_designation_no_dates():
    """Scenario 9: Candidate mentions company and designation but no dates."""
    raw_exp = {
        "industry": [
            {
                "company_name": "ABC Technologies",
                "job_title": "Software Engineer",
                "start_date": None,
                "end_date": None,
                "duration_years": 0.0
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    # Must preserve record without inventing dates
    assert len(enriched["industry"]) == 1
    assert enriched["industry"][0]["company_name"] == "ABC Technologies"
    assert enriched["industry"][0]["job_title"] == "Software Engineer"
    assert enriched["industry"][0]["start_date"] is None
    assert enriched["industry"][0]["end_date"] is None
    # Experience status must be unavailable, not zero_experience (distinction required by prompt)
    assert enriched["experience_status"] == "unavailable"
    assert enriched["calculated_total_years"] == 0.0


def test_scenario_10_internship_experience_only():
    """Scenario 10: Candidate has internship experience only."""
    raw_exp = {
        "industry": [
            {
                "company_name": "Startup Hub",
                "job_title": "Software Engineering Intern",
                "start_date": "June 2023",
                "end_date": "August 2023",
                "is_internship": True,
                "employment_type": "internship"
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    # Internships should not be counted as full-time professional experience
    assert enriched["industry"][0]["is_internship"] is True
    assert enriched["calculated_total_years"] == 0.0
    assert enriched["experience_status"] == "unavailable"


def test_scenario_11_freelance_experience():
    """Scenario 11: Candidate has freelance experience."""
    raw_exp = {
        "industry": [
            {
                "company_name": "Self-Employed / Upwork",
                "job_title": "Freelance Full-Stack Developer",
                "start_date": "January 2020",
                "end_date": "December 2022",
                "employment_type": "freelance"
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    assert enriched["industry"][0]["employment_type"] == "freelance"
    assert enriched["calculated_total_years"] >= 2.9
    assert enriched["experience_status"] == "available"


def test_scenario_12_employment_gaps():
    """Scenario 12: Candidate has employment gaps. Gaps must not be counted."""
    raw_exp = {
        "industry": [
            {
                "company_name": "Company One",
                "job_title": "Developer",
                "start_date": "January 2015",
                "end_date": "December 2017"  # 3 yrs (2015-2017)
            },
            # Gap of 3 years (2018, 2019, 2020)
            {
                "company_name": "Company Two",
                "job_title": "Senior Developer",
                "start_date": "January 2021",
                "end_date": "December 2023"  # 3 yrs (2021-2023)
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    # 3 yrs + 3 yrs = 6 yrs (NOT 2023 - 2015 = 9 yrs)
    assert enriched["calculated_total_years"] == pytest.approx(6.0, abs=0.2)
    assert enriched["calculation_basis"] == "calculated_from_history"


def test_scenario_13_discrepancy_explicit_vs_calculated():
    """Scenario 13: Candidate has explicit experience that disagrees with calculated experience."""
    raw_exp = {
        "explicitly_mentioned_years": 10.0,
        "explicit_experience_text": "10 years of experience",
        "industry": [
            {
                "company_name": "Sole Employer",
                "job_title": "Software Engineer",
                "start_date": "January 2022",
                "end_date": "December 2023"  # Only 2 years in reality!
            }
        ]
    }
    enriched = calculate_and_enrich_experience(raw_exp, current_year=TEST_CURRENT_YEAR)

    assert enriched["explicitly_mentioned_years"] == 10.0
    assert enriched["calculated_total_years"] == pytest.approx(2.0, abs=0.2)
    assert enriched["experience_status"] == "discrepancy_detected"
    assert enriched["calculation_basis"] == "discrepancy"
    assert enriched["discrepancy_note"] is not None
    assert "Discrepancy detected" in enriched["discrepancy_note"]


def test_scenario_14_no_identifiable_employment_history():
    """Scenario 14: Candidate has no identifiable employment history (Fresh Graduate)."""
    text = (
        "ANANYA PATEL\n"
        "Email: ananya@example.com | Phone: +91 9999988888\n"
        "EDUCATION\n"
        "B.Tech in Information Technology | MIT Pune | 2024 | CGPA: 9.1\n"
        "ACADEMIC PROJECTS\n"
        "Deep Learning based Plant Disease Detection using PyTorch\n"
        "SKILLS\n"
        "Python, C++, Java, Machine Learning, Git"
    )
    enriched = calculate_and_enrich_experience({}, full_resume_text=text, current_year=TEST_CURRENT_YEAR)

    assert enriched["calculated_total_years"] == 0.0
    assert enriched["explicitly_mentioned_years"] is None
    assert enriched["experience_status"] == "zero_experience"
    assert enriched["calculation_basis"] == "not_specified"


def test_schema_backward_compatibility():
    """Test Pydantic schema validation for ExperienceContainer with both new and old fields."""
    data = {
        "explicitly_mentioned_years": 8.0,
        "explicit_experience_text": "8+ years of experience",
        "calculated_total_years": 8.0,
        "calculation_basis": "explicitly_stated",
        "experience_status": "available",
        "academic": [
            {
                "institution": "Stanford University",
                "role": "Postdoctoral Researcher",
                "start_date": "2016",
                "end_date": "2018",
                "duration_years": 2.0
            }
        ],
        "industry": [
            {
                "company_name": "Google",
                "job_title": "Senior Staff Engineer",
                "start_date": "2018",
                "end_date": "Present",
                "is_current": True,
                "duration_years": 6.0
            }
        ]
    }
    container = ExperienceContainer(**data)
    d = container.model_dump()
    assert d["explicitly_mentioned_years"] == 8.0
    # Check harmonization
    assert d["academic"][0]["company_name"] == "Stanford University"
    assert d["industry"][0]["organization"] == "Google"
    assert d["industry"][0]["role"] == "Senior Staff Engineer"


# ==============================================================================
# PART 1 TESTS: Dict of Lists (Academic & Professional), Anti-Pollution, Total Experience
# ==============================================================================

from backend.app.schemas.candidate import ExperienceItem, ExperienceContainer, CandidateSchema
from backend.app.llm.experience_calculator import (
    clean_and_calculate_experience_dict,
    clean_and_calculate_experience_list,
    is_unrelated_experience_item
)


def test_part1_dict_of_lists_schema():
    """Test experience structure is a dictionary with two sections: academic and professional."""
    raw_exp = {
        "academic": [
            {
                "institution": "National Institute of Science",
                "role": "Senior Research Fellow (SRF)",
                "start_date": "2019",
                "end_date": "2021",
                "duration_years": 2.0,
                "description": "Fellowship"
            }
        ],
        "professional": [
            {
                "institution": "Delhi Technological University",
                "role": "Assistant Professor",
                "start_date": "2021",
                "end_date": "Present",
                "duration_years": 4.5,
                "description": "Teaching CS courses"
            }
        ]
    }
    cleaned_dict, total_exp = clean_and_calculate_experience_dict(raw_exp, current_year=2026)
    assert isinstance(cleaned_dict, dict)
    assert "academic" in cleaned_dict
    assert "professional" in cleaned_dict
    assert len(cleaned_dict["academic"]) == 1
    assert len(cleaned_dict["professional"]) == 1
    assert cleaned_dict["academic"][0]["role"] == "Senior Research Fellow (SRF)"
    assert cleaned_dict["professional"][0]["role"] == "Assistant Professor"
    assert total_exp >= 6.0


def test_part1_research_fellowship_as_academic_and_teaching_as_professional():
    """
    Research fellowship / research scholar / JRF / SRF / Postdoc are in 'academic'.
    Actual teaching faculty (Professor, Lecturer) and industry roles are in 'professional'.
    """
    raw_list = [
        {
            "institution": "National Institute of Science",
            "role": "Senior Research Fellow (SRF)",
            "start_date": "2019",
            "end_date": "2021",
            "duration_years": 2.0
        },
        {
            "institution": "Tufts University",
            "role": "Postdoctoral Research Scholar",
            "start_date": "2021",
            "end_date": "2023",
            "duration_years": 2.0
        },
        {
            "institution": "State University",
            "role": "Assistant Professor",
            "start_date": "2023",
            "end_date": "Present",
            "duration_years": 3.0
        },
        {
            "institution": "Tech Mahindra Ltd",
            "role": "Software Developer",
            "start_date": "2016",
            "end_date": "2018",
            "duration_years": 2.0
        }
    ]

    cleaned_dict, total = clean_and_calculate_experience_dict(raw_list, current_year=2026)
    assert len(cleaned_dict["academic"]) == 2  # SRF + Postdoc
    assert len(cleaned_dict["professional"]) == 2  # Assistant Professor + Software Developer
    acad_roles = [x["role"] for x in cleaned_dict["academic"]]
    prof_roles = [x["role"] for x in cleaned_dict["professional"]]
    assert "Senior Research Fellow (SRF)" in acad_roles
    assert "Postdoctoral Research Scholar" in acad_roles
    assert "Assistant Professor" in prof_roles
    assert "Software Developer" in prof_roles
    assert total >= 9.0


def test_part1_anti_pollution_excludes_unrelated_information():
    """Anti-pollution: NAAC, accreditation, research topics, publications, academic projects, thesis, degrees, certs must NOT be in experience."""
    polluted_items = [
        {
            "institution": "University XYZ",
            "role": "NAAC A+ Accreditation Committee Member",
            "start_date": "2020",
            "end_date": "2021"
        },
        {
            "institution": "ABC College",
            "role": "Research Interests: Deep Learning and NLP",
            "start_date": None,
            "end_date": None
        },
        {
            "institution": "IEEE Transactions",
            "role": "Journal Articles on Transformer Models",
            "start_date": "2022",
            "end_date": "2022"
        },
        {
            "institution": "IIT Bombay",
            "role": "M.Tech Thesis: Optimization of CNNs",
            "start_date": "2014",
            "end_date": "2016"
        },
        {
            "institution": "NPTEL",
            "role": "Online Certificate in Cloud Computing",
            "start_date": "2021",
            "end_date": "2021"
        },
        {
            "institution": "Delhi Technological University",
            "role": "Assistant Professor",
            "start_date": "2018",
            "end_date": "Present",
            "duration_years": None
        }
    ]

    for item in polluted_items[:5]:
        assert is_unrelated_experience_item(item) is True

    cleaned_dict, total = clean_and_calculate_experience_dict(polluted_items, current_year=2026)
    # Only the genuine Assistant Professor role survives, in professional section
    assert len(cleaned_dict["academic"]) == 0
    assert len(cleaned_dict["professional"]) == 1
    assert cleaned_dict["professional"][0]["role"] == "Assistant Professor"
    assert total > 0.0


def test_part1_duration_determination_from_dates_and_current():
    """
    If dates are given without duration, determine duration from dates.
    Recognize Present, Current, Till Date, Ongoing, Now.
    Preserve records where dates are null.
    """
    items = {
        "academic": [],
        "professional": [
            {
                "institution": "Christ University",
                "role": "Assistant Professor",
                "start_date": "2018",
                "end_date": "Present",
                "duration_years": 0.0,
                "description": None
            },
            {
                "institution": "Infosys",
                "role": "Systems Engineer",
                "start_date": None,
                "end_date": None,
                "duration_years": 0.0,
                "description": "Banking client project"
            }
        ]
    }

    cleaned_dict, total = clean_and_calculate_experience_dict(items, current_year=2026, current_month=1)
    prof = cleaned_dict["professional"]
    assert len(prof) == 2
    # Christ University: 2018.0 to 2026.08 => ~8 years (not 0!)
    assert prof[0]["duration_years"] >= 7.9
    # Infosys: dates null, preserved, not discarded
    assert prof[1]["institution"] == "Infosys"
    assert prof[1]["start_date"] is None
    assert prof[1]["end_date"] is None
    assert total >= 7.9


def test_part1_total_experience_overlapping_not_double_counted():
    """Overlapping employment periods must not be double counted in candidate-level total_experience."""
    items = {
        "academic": [],
        "professional": [
            {
                "institution": "University A",
                "role": "Lecturer",
                "start_date": "2016-01",
                "end_date": "2020-01",  # 4 years (2016.0 to 2020.08)
                "duration_years": 4.0
            },
            {
                "institution": "Company B (Consultancy / Part-time)",
                "role": "Technical Consultant",
                "start_date": "2018-01",
                "end_date": "2022-01",  # 4 years (2018.0 to 2022.08)
                "duration_years": 4.0
            }
        ]
    }

    # Without overlap handling: 4 + 4 = 8 years.
    # With interval union: 2016 to 2022 = 6 years.
    cleaned_dict, total = clean_and_calculate_experience_dict(items, current_year=2026)
    assert 5.9 <= total <= 6.1


def test_part1_candidate_schema_with_dict_of_lists_experience():
    """CandidateSchema accepts ExperienceContainer as dict of lists and candidate-level total_experience."""
    candidate_data = {
        "candidate_id": "CAND-0099",
        "source_file": "sample_cv.pdf",
        "personal_information": {
            "full_name": "Dr. Jane Doe",
            "email": "jane@example.edu"
        },
        "education": [],
        "publications": [],
        "experience": {
            "academic": [
                {
                    "institution": "Harvard University",
                    "role": "Postdoctoral Fellow",
                    "start_date": "2017",
                    "end_date": "2020",
                    "duration_years": 3.0,
                    "description": "Quantum machine learning"
                }
            ],
            "professional": [
                {
                    "institution": "MIT",
                    "role": "Assistant Professor",
                    "start_date": "2020",
                    "end_date": "Present",
                    "duration_years": 6.0,
                    "description": "Teaching CS"
                }
            ]
        },
        "total_experience": 9.0
    }

    cand = CandidateSchema(**candidate_data)
    assert cand.total_experience == 9.0
    assert len(cand.experience.academic) == 1
    assert len(cand.experience.professional) == 1
    assert cand.experience.academic[0].role == "Postdoctoral Fellow"
    assert cand.experience.professional[0].role == "Assistant Professor"


def test_part1_realistic_resume_snehamoy_pramanik():
    """Test extraction on Snehamoy Pramanik (R-035): Assistant Professor in professional and Postdoc in academic."""
    raw_exp = {
        "academic": [
            {
                "institution": "Tufts University",
                "role": "Post Doctoral Fellow",
                "start_date": "2020",
                "end_date": "2021",
                "duration_years": 1.0,
                "description": "Postdoctoral research"
            }
        ],
        "professional": [
            {
                "institution": "Department of Mathematics, CHRIST (Deemed to be university), Bangalore, India",
                "role": "Assistant Professor",
                "start_date": "2022",
                "end_date": "Present",
                "duration_years": None,
                "description": None
            }
        ]
    }
    cleaned_dict, total = clean_and_calculate_experience_dict(raw_exp, current_year=2026, current_month=1)
    assert len(cleaned_dict["academic"]) == 1
    assert len(cleaned_dict["professional"]) == 1
    assert cleaned_dict["academic"][0]["role"] == "Post Doctoral Fellow"
    assert cleaned_dict["professional"][0]["role"] == "Assistant Professor"
    # 2020-2021 (1.0) + 2022-2026 (~4.0) = ~5.0 years (not 0!)
    assert total >= 4.9
    assert cleaned_dict["professional"][0]["duration_years"] >= 3.9


def test_part1_realistic_resume_01_eric_nalisnick():
    """Test extraction on Eric Nalisnick: Postdoc in academic + Faculty and DeepMind in professional."""
    raw_exp = {
        "academic": [
            {
                "institution": "University of Cambridge",
                "role": "Postdoctoral Research Associate",
                "start_date": "September 2018",
                "end_date": "September 2020",
                "duration_years": 2.0
            }
        ],
        "professional": [
            {
                "institution": "Johns Hopkins University",
                "role": "Assistant Professor, Tenure Track",
                "start_date": "March 2024",
                "end_date": "Present",
                "duration_years": None
            },
            {
                "institution": "University of Amsterdam",
                "role": "Assistant Professor, Tenure Track",
                "start_date": "September 2020",
                "end_date": "February 2024",
                "duration_years": None
            },
            {
                "institution": "Google DeepMind",
                "role": "Research Scientist",
                "start_date": "February 2019",
                "end_date": "January 2020",
                "duration_years": 1.0
            }
        ]
    }
    cleaned_dict, total = clean_and_calculate_experience_dict(raw_exp, current_year=2026, current_month=1)
    assert len(cleaned_dict["academic"]) == 1
    assert len(cleaned_dict["professional"]) == 3
    # DeepMind overlaps with Cambridge; interval union handles overlap
    assert total >= 7.0


def test_part1_realistic_resume_02_charu_jain():
    """Test extraction on Charu Jain: Teaching Experience 11 years 4 months in professional."""
    full_text = (
        "Ramanujan College\n"
        "FACULTY PROFILE: CHARU JAIN\n"
        "DESIGNATION: ASSISTANT PROFESSOR\n"
        "CAREER PROFILE: TEACHING EXPERIENCE\n"
        "11 years and 4 months Teaching Experience\n"
        "CAREER PROFILE: INDUSTRY EXPERIENCE\n"
        "No Industry Experience"
    )
    raw_exp = {
        "academic": [],
        "professional": [
            {
                "institution": "Ramanujan College, University of Delhi",
                "role": "Assistant Professor",
                "start_date": None,
                "end_date": "Present",
                "duration_years": 11.33,
                "description": "Teaching Experience"
            }
        ]
    }
    cleaned_dict, total = clean_and_calculate_experience_dict(raw_exp, raw_total_exp=11.33, full_resume_text=full_text, current_year=2026)
    assert len(cleaned_dict["professional"]) == 1
    assert cleaned_dict["professional"][0]["duration_years"] == 11.33
    assert total == 11.33


def test_part1_realistic_resume_15_reena_rani():
    """Test extraction on Reena Rani: Teaching: 5 Years 10 Months in professional with NPTEL filtered."""
    full_text = (
        "Name : Mrs. R. Reena Rani\n"
        "Designation : Assistant Professor\n"
        "Department : English\n"
        "Experience : Teaching: 5 Years 10 Months\n"
        "Diploma / Vocational / Certification: Enhancing Soft Skill and Personality, NPTEL, 2019\n"
        "Participation in Conference: International Conference on English Language Teaching"
    )
    raw_exp = {
        "academic": [],
        "professional": [
            {
                "institution": "Dr. NGP Arts and Science College",
                "role": "Assistant Professor",
                "start_date": None,
                "end_date": "Present",
                "duration_years": 5.83,
                "description": "Teaching: 5 Years 10 Months"
            },
            {
                "institution": "NPTEL",
                "role": "Online Certificate Enhancing Soft Skill",
                "start_date": "2019",
                "end_date": "2019"
            }
        ]
    }
    cleaned_dict, total = clean_and_calculate_experience_dict(raw_exp, raw_total_exp=5.83, full_resume_text=full_text, current_year=2026)
    assert len(cleaned_dict["professional"]) == 1
    assert cleaned_dict["professional"][0]["role"] == "Assistant Professor"
    assert total == 5.83


def test_part1_realistic_resume_18_swathi():
    """Test extraction on Matta Swathi: 8+ Years faculty in professional with Areas of Research filtered."""
    raw_exp = {
        "academic": [],
        "professional": [
            {
                "institution": "Lakireddy Bali Reddy College of Engineering",
                "role": "Sr.Assistant Professor",
                "start_date": "Dec, 2025",
                "end_date": "Till Date",
                "duration_years": None
            },
            {
                "institution": "Lakireddy Bali Reddy College of Engineering",
                "role": "Assistant Professor",
                "start_date": "Aug, 2021",
                "end_date": "Nov, 2025",
                "duration_years": 4.25
            },
            {
                "institution": "Paladugu Parvathi Devi College of Engineering & Technology",
                "role": "Assistant Professor",
                "start_date": "June, 2017",
                "end_date": "December, 2020",
                "duration_years": 3.5
            },
            {
                "institution": "College",
                "role": "Areas of Research : Generative AI, Artificial intellience",
                "start_date": None,
                "end_date": None
            }
        ]
    }
    cleaned_dict, total = clean_and_calculate_experience_dict(raw_exp, raw_total_exp=8.0, current_year=2026, current_month=1)
    assert len(cleaned_dict["professional"]) == 3
    assert len(cleaned_dict["academic"]) == 0
    assert total >= 8.0
