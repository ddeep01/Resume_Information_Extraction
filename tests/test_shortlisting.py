import pytest
from backend.app.shortlisting.degree_matcher import normalize_degree_name, matches_required_degree
from backend.app.shortlisting.specialization_matcher import matches_specialization
from backend.app.shortlisting.eligibility import evaluate_candidate_eligibility
from backend.app.shortlisting.scoring import (
    calculate_education_score,
    calculate_publication_score,
    calculate_academic_experience_score,
    calculate_industry_experience_score,
    calculate_final_score
)
from backend.app.shortlisting.ranking import rank_and_shortlist_candidates

def test_degree_normalization():
    assert normalize_degree_name("Ph.D.") == "PhD"
    assert normalize_degree_name("Doctor of Philosophy") == "PhD"
    assert normalize_degree_name("Master of Technology") == "M.Tech"
    assert normalize_degree_name("Bachelor of Science") == "B.Sc."

def test_degree_matching():
    candidate_edu = [{"degree": "Ph.D.", "stream": "Computer Science"}]
    matched, reason = matches_required_degree("PhD", candidate_edu)
    assert matched is True

    candidate_edu_ug = [{"degree": "B.Tech", "stream": "Computer Science"}]
    matched_ug, reason_ug = matches_required_degree("PhD", candidate_edu_ug)
    assert matched_ug is False

def test_specialization_matching():
    matched, reason = matches_specialization("Computer Science", ["Computer Science and Engineering"])
    assert matched is True

def test_scoring_and_ranking():
    edu_score = calculate_education_score([{"qualification_type": "PhD", "institution_score": 1.0}])
    pub_score = calculate_publication_score([{"venue_score": 1.0}, {"venue_score": 0.66}], target_min_pubs=2)
    acad_score = calculate_academic_experience_score([{"duration_years": 5.0, "institution_score": 1.0}])
    ind_score = calculate_industry_experience_score([{"duration_years": 2.0}])

    weights = {"education": 0.35, "publication": 0.30, "academic_experience": 0.20, "industry_experience": 0.15}
    final_score = calculate_final_score(edu_score, pub_score, acad_score, ind_score, weights)

    assert 0.0 <= final_score <= 100.0

    candidates = [
        {
            "candidate_id": "CAND-0001",
            "shortlisting": {"eligible": True, "final_score": 85.0, "reasons": []}
        },
        {
            "candidate_id": "CAND-0002",
            "shortlisting": {"eligible": True, "final_score": 92.0, "reasons": []}
        },
        {
            "candidate_id": "CAND-0003",
            "shortlisting": {"eligible": False, "final_score": 40.0, "reasons": []}
        }
    ]

    ranked = rank_and_shortlist_candidates(candidates, top_n=1)
    shortlisted = [c for c in ranked if c["shortlisting"]["shortlisted"]]
    assert len(shortlisted) == 1
    assert shortlisted[0]["candidate_id"] == "CAND-0002"
    assert shortlisted[0]["shortlisting"]["rank"] == 1
