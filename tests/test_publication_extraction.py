import pytest
from datetime import datetime
from backend.app.schemas.candidate import PublicationItem, CandidateSchema, LLMExtractionRaw
from backend.app.llm.extraction import LLMExtractor
from backend.app.llm.merger import HierarchicalMerger
from backend.app.shortlisting.eligibility import filter_publications_by_window, evaluate_candidate_eligibility
from backend.app.classification.publication_classifier import PublicationClassifier


# ==============================================================================
# 1. PublicationItem Schema Validation Tests
# ==============================================================================

def test_publication_item_valid_schema():
    """Verify standard publication conforms to schema with all fields populated."""
    item = PublicationItem(
        publication_type="journal",
        publication_name="Are Vision Language Models Robust to Classic Uncertainty Challenges?",
        venue_name="Transactions on Machine Learning Research (TMLR)",
        published_at="2026-01",
        publication_year=2026
    )
    dumped = item.model_dump()
    assert dumped["publication_type"] == "journal"
    assert dumped["publication_name"] == "Are Vision Language Models Robust to Classic Uncertainty Challenges?"
    assert dumped["venue_name"] == "Transactions on Machine Learning Research (TMLR)"
    assert dumped["published_at"] == "2026-01"
    assert dumped["publication_year"] == 2026
    assert dumped["venue_tier"] == "Tier 3"
    assert dumped["venue_score"] == 0.33
    assert dumped["in_publication_window"] is True


def test_publication_item_never_allows_year_as_venue():
    """Verify 4-digit years like '2023' are rejected as venue_name and set to None."""
    item = PublicationItem(
        publication_type="journal",
        publication_name="Deep Learning Foundations",
        venue_name="2023",
        publication_year=2023
    )
    assert item.venue_name is None
    assert item.publication_year == 2023

    item2 = PublicationItem(
        publication_type="conference",
        publication_name="Neural Architectures",
        venue_name=" 2024 ",
        published_at="2024"
    )
    assert item2.venue_name is None
    assert item2.publication_year == 2024


def test_publication_item_type_normalization():
    """Verify publication_type strings are normalized to valid categories."""
    assert PublicationItem(publication_name="Paper A", publication_type="Refereed Journal Article").publication_type == "journal"
    assert PublicationItem(publication_name="Paper B", publication_type="International Conference Proceedings").publication_type == "conference"
    assert PublicationItem(publication_name="Paper C", publication_type="Workshop").publication_type == "conference"
    assert PublicationItem(publication_name="Paper D", publication_type="Book Chapter in AI").publication_type == "book_chapter"
    assert PublicationItem(publication_name="Paper E", publication_type="Authored Book").publication_type == "book"
    assert PublicationItem(publication_name="Paper F", publication_type="Utility Patent").publication_type == "patent"
    assert PublicationItem(publication_name="Paper G", publication_type="arXiv Preprint").publication_type == "other"


def test_publication_item_title_prefix_stripping():
    """Verify titles with prefixes ('Paper Title:', '1. ', quotes) are cleaned."""
    item1 = PublicationItem(publication_name='1. Paper Title “Need and Importance of Strategic Human Resource Management “')
    assert item1.publication_name == "Need and Importance of Strategic Human Resource Management"

    item2 = PublicationItem(publication_name='• Title: Deep learning for real-time colon polyp detection.')
    assert item2.publication_name == "Deep learning for real-time colon polyp detection"


def test_publication_item_year_inferred_from_published_at():
    """Verify publication_year is inferred if published_at contains a 4-digit year."""
    item = PublicationItem(
        publication_name="Quantum Computing Algorithms",
        venue_name="Nature Physics",
        published_at="March 2025"
    )
    assert item.publication_year == 2025


def test_publication_item_preserves_partial_missing_info():
    """Verify genuine publications with missing venue or missing year are preserved with nulls."""
    item = PublicationItem(
        publication_name="Unpublished Preliminary Manuscript on Graph Neural Networks",
        venue_name=None,
        published_at=None,
        publication_year=None
    )
    assert item.publication_name == "Unpublished Preliminary Manuscript on Graph Neural Networks"
    assert item.venue_name is None
    assert item.publication_year is None


# ==============================================================================
# 2. Extractor Cleaning & Anti-Pollution Tests
# ==============================================================================

class DummyProvider:
    def generate(self, prompt: str, system: str = "") -> str:
        return "{}"


def test_extractor_cleans_template_placeholders():
    """Verify extractor discards template placeholder titles."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {"publication_name": "Title of paper or patent", "venue_name": "Venue"},
            {"publication_name": "Actual paper/publication title", "venue_name": "Venue"},
            {"publication_name": "Real Paper Title", "venue_name": "Real Venue", "publication_year": 2024}
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 1
    assert cleaned["publications"][0]["publication_name"] == "Real Paper Title"


def test_extractor_anti_pollution_thesis_and_coursework():
    """Verify theses, capstone projects, and coursework are filtered out from publications."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {"publication_name": "PhD Thesis: On Priors for Bayesian Neural Networks", "venue_name": "UC Irvine"},
            {"publication_name": "Master's Thesis: Automatic Methods for Sentiment Tracking", "venue_name": "Lehigh University"},
            {"publication_name": "B.Tech Project: Hospital Management System", "venue_name": "College"},
            {"publication_name": "Capstone Project: Autonomous Navigation", "venue_name": "Robotics Lab"},
            {"publication_name": "Coursework: Advanced Distributed Operating Systems", "venue_name": "Univ"},
            {"publication_name": "Monitoring Risks in Test-Time Adaptation", "venue_name": "NeurIPS", "publication_year": 2025}
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 1
    assert cleaned["publications"][0]["publication_name"] == "Monitoring Risks in Test-Time Adaptation"


# ==============================================================================
# 3. Hierarchical Merger Publication Deduplication Tests
# ==============================================================================

def test_merger_publication_deduplication_and_complementary_fields():
    """Verify merger deduplicates identical papers and combines complementary fields."""
    merger = HierarchicalMerger(provider=DummyProvider())
    part1 = {
        "publications": [
            {
                "publication_type": "journal",
                "publication_name": "Normalizing Flows for Probabilistic Modeling and Inference",
                "venue_name": "Journal of Machine Learning Research (JMLR)",
                "publication_year": 2021
            }
        ]
    }
    part2 = {
        "publications": [
            {
                "publication_type": "journal",
                "publication_name": '“Normalizing Flows for Probabilistic Modeling and Inference”',
                "venue_name": "Journal of Machine Learning Research (JMLR)",
                "published_at": "2021-08"
            }
        ]
    }
    merged = merger.python_deterministic_merge(part1, part2)
    assert len(merged["publications"]) == 1
    pub = merged["publications"][0]
    assert pub["publication_name"] == "Normalizing Flows for Probabilistic Modeling and Inference"
    assert pub["venue_name"] == "Journal of Machine Learning Research (JMLR)"
    assert pub["publication_year"] == 2021
    assert pub["published_at"] == "2021-08"


# ==============================================================================
# 4. Realistic Resume Publication Extraction Scenarios
# ==============================================================================

def test_scenario_resume_01_eric_nalisnick():
    """Test realistic publication parsing on Eric Nalisnick: journals, conferences, workshops."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {
                "publication_type": "journal",
                "publication_name": "Are Vision Language Models Robust to Classic Uncertainty Challenges?",
                "venue_name": "Transactions on Machine Learning Research (TMLR)",
                "published_at": "2026",
                "publication_year": 2026
            },
            {
                "publication_type": "journal",
                "publication_name": "A Brief Tour of Deep Learning from a Statistical Perspective",
                "venue_name": "Annual Review of Statistics and Its Application",
                "published_at": "2023",
                "publication_year": 2023
            },
            {
                "publication_type": "conference",
                "publication_name": "Monitoring Risks in Test-Time Adaptation",
                "venue_name": "Advances in Neural Information Processing Systems (NeurIPS)",
                "published_at": "2025",
                "publication_year": 2025
            },
            {
                "publication_type": "conference",
                "publication_name": "Max-Rank: Efficient Multiple Testing for Conformal Prediction",
                "venue_name": "Proceedings of the 28th International Conference on Artificial Intelligence and Statistics (AISTATS)",
                "published_at": "2025",
                "publication_year": 2025
            }
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 4
    for p in cleaned["publications"]:
        assert p["venue_name"] != "2025" and p["venue_name"] != "2026" and p["venue_name"] != "2023"
        assert p["publication_year"] in (2023, 2025, 2026)


def test_scenario_resume_02_charu_jain():
    """Test Charu Jain: 4 research papers extracted from PUBLICATIONS PROFILE; workshops/FDPs excluded."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {
                "publication_type": "journal",
                "publication_name": 'Paper Title “Need and Importance of Strategic Human Resource Management “',
                "venue_name": "International Research Journal of Management Science and Technology",
                "published_at": "2014",
                "publication_year": 2014
            },
            {
                "publication_type": "journal",
                "publication_name": 'Paper Title “Relevance of Ethical Values in Education”',
                "venue_name": "International Journal of Applied Ethics",
                "published_at": "2014-2015",
                "publication_year": 2014
            },
            {
                "publication_type": "journal",
                "publication_name": 'Paper Title “Stress Management”',
                "venue_name": "Indian Streams Research Journal",
                "published_at": "March 2015",
                "publication_year": 2015
            },
            {
                "publication_type": "journal",
                "publication_name": 'Paper Title “Succession Management”',
                "venue_name": "Golden Research Thoughts",
                "published_at": "March-2015",
                "publication_year": 2015
            }
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 4
    titles = [p["publication_name"] for p in cleaned["publications"]]
    assert "Need and Importance of Strategic Human Resource Management" in titles
    assert "Relevance of Ethical Values in Education" in titles
    assert "Stress Management" in titles
    assert "Succession Management" in titles


def test_scenario_resume_03_hamed_pirsiavash():
    """Test Hamed Pirsiavash: US patents and top-tier conference publications."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {
                "publication_type": "patent",
                "publication_name": "Systems and methods for indexing presentation videos",
                "venue_name": "US08280158",
                "published_at": "10/2014",
                "publication_year": 2014
            },
            {
                "publication_type": "patent",
                "publication_name": "Deep learning for real-time colon polyp detection",
                "venue_name": "US11308614B2",
                "published_at": None,
                "publication_year": None
            },
            {
                "publication_type": "conference",
                "publication_name": "MCNC: Manifold-Constrained Reparameterization for Neural Compression",
                "venue_name": "International Conference on Learning Representations (ICLR)",
                "published_at": "2025",
                "publication_year": 2025
            },
            {
                "publication_type": "journal",
                "publication_name": "A collective AI via lifelong learning and sharing at the edge",
                "venue_name": "Nature Machine Intelligence",
                "published_at": "2024",
                "publication_year": 2024
            }
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 4
    patents = [p for p in cleaned["publications"] if p["publication_type"] == "patent"]
    assert len(patents) == 2
    assert patents[0]["publication_name"] == "Systems and methods for indexing presentation videos"
    assert patents[1]["venue_name"] == "US11308614B2"


def test_scenario_resume_15_reena_rani_empty_publications():
    """Test Reena Rani: resume has only conference attendances, seminars, and FDPs -> 0 publications."""
    extractor = LLMExtractor(provider=DummyProvider())
    # LLM correctly ignores conference attendances and workshop participations
    raw_dict = {
        "personal_information": {"full_name": "Mrs. R. Reena Rani"},
        "education": [{"degree": "M.Phil", "university": "Bharathiar University"}],
        "publications": [],
        "experience": {"academic": [], "professional": [{"institution": "Dr. NGP College", "role": "Assistant Professor", "duration_years": 5.83}]}
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 0


def test_scenario_resume_18_matta_swathi():
    """Test Matta Swathi: Extracts 2 published patents, ignores NPTEL certs and research interests."""
    extractor = LLMExtractor(provider=DummyProvider())
    raw_dict = {
        "publications": [
            {
                "publication_type": "patent",
                "publication_name": "Published 2 Patents (1 Utility & 1 Design)",
                "venue_name": "Indian Patent Office",
                "published_at": "2024-2025",
                "publication_year": 2024
            }
        ]
    }
    cleaned = extractor.verify_and_clean_data(raw_dict)
    assert len(cleaned["publications"]) == 1
    assert cleaned["publications"][0]["publication_type"] == "patent"
    assert cleaned["publications"][0]["publication_year"] == 2024


# ==============================================================================
# 5. Shortlisting & Publication Window Filter Tests
# ==============================================================================

def test_filter_publications_by_window():
    """Verify publication window filtering correctly flags in_publication_window."""
    pubs = [
        {"publication_name": "Paper 2026", "publication_year": 2026},
        {"publication_name": "Paper 2024", "publication_year": 2024},
        {"publication_name": "Paper 2020", "publication_year": 2020},
        {"publication_name": "Paper 2015", "publication_year": 2015},
        {"publication_name": "Paper No Date", "publication_year": None, "published_at": None}
    ]
    # Current year = 2026, window = 3 years -> min_year = 2023
    filtered = filter_publications_by_window(pubs, window_years=3, current_year=2026)
    # 2026 (yes), 2024 (yes), 2020 (no), 2015 (no), No Date (yes by default)
    assert len(filtered) == 3
    valid_titles = [p["publication_name"] for p in filtered]
    assert "Paper 2026" in valid_titles
    assert "Paper 2024" in valid_titles
    assert "Paper No Date" in valid_titles
    assert "Paper 2020" not in valid_titles


def test_evaluate_candidate_eligibility_publication_criteria():
    """Verify evaluation respects minimum publications within window."""
    candidate = {
        "education": [{"degree": "Ph.D.", "stream": "Computer Science"}],
        "experience": {"professional": [{"role": "Assistant Professor", "duration_years": 5.0}]},
        "total_experience": 5.0,
        "publications": [
            {"publication_name": "Recent Paper 1", "publication_year": 2025, "venue_name": "NeurIPS"},
            {"publication_name": "Recent Paper 2", "publication_year": 2024, "venue_name": "ICLR"},
            {"publication_name": "Old Paper 1", "publication_year": 2014, "venue_name": "Conference"}
        ]
    }
    # Require 2 publications in 3 year window -> Should PASS
    is_eligible, reasons, window_pubs, total_exp = evaluate_candidate_eligibility(
        candidate,
        required_degree="Ph.D.",
        required_specialization="Computer Science",
        minimum_experience=3.0,
        minimum_publications=2,
        publication_window_years=3
    )
    assert is_eligible is True
    assert len(window_pubs) == 2
    assert any("Publication criteria met" in r for r in reasons)

    # Require 3 publications in 3 year window -> Should FAIL (only 2 in window)
    is_eligible_fail, reasons_fail, window_pubs_fail, _ = evaluate_candidate_eligibility(
        candidate,
        required_degree="Ph.D.",
        required_specialization="Computer Science",
        minimum_experience=3.0,
        minimum_publications=3,
        publication_window_years=3
    )
    assert is_eligible_fail is False
    assert any("Publication criteria NOT met" in r for r in reasons_fail)
