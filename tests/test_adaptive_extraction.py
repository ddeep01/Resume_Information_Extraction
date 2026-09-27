import json
import pytest
from typing import Optional
from backend.app.config import settings
from backend.app.llm.base import LLMProvider
from backend.app.llm.token_counter import TokenCounter
from backend.app.llm.splitter import RecursiveTextSplitter
from backend.app.llm.json_validator import JSONValidator
from backend.app.llm.merger import HierarchicalMerger
from backend.app.llm.extraction import LLMExtractor
from backend.app.classification.publication_classifier import PublicationClassifier

class MockLLMProvider(LLMProvider):
    def __init__(self, default_response: Optional[str] = None):
        self.call_count = 0
        self.prompts_received = []
        self.default_response = default_response
        self.fail_chunks = set()
        self.timeout_chunks = set()
        self.malformed_json_once = set()

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        self.call_count += 1
        self.prompts_received.append(prompt)

        # Check if set to simulate timeout
        for t_key in list(self.timeout_chunks):
            if t_key in prompt:
                self.timeout_chunks.remove(t_key) # timeout once then proceed
                raise RuntimeError("Ollama API request error: HTTP read timeout after 120s")

        # Check if set to simulate malformed json
        for m_key in list(self.malformed_json_once):
            if m_key in prompt:
                self.malformed_json_once.remove(m_key)
                return "INVALID JSON {{{ missing brace: 123"

        if self.default_response:
            return self.default_response

        # Default structured JSON response generator based on prompt content
        if "PARTIAL RESULT" in prompt or "merging partial extraction" in prompt:
            return json.dumps({
                "personal_information": {
                    "full_name": "Dr. Jane Smith",
                    "current_designation": "Senior Researcher",
                    "email": "jane.smith@lab.org",
                    "phone": "+1-555-0199"
                },
                "education": [
                    {
                        "qualification_type": "PhD",
                        "degree": "PhD",
                        "stream": "Computer Science",
                        "university": "Stanford University",
                        "year": "2018",
                        "cgpa": "3.9"
                    }
                ],
                "publications": [
                    {
                        "publication_type": "journal",
                        "publication_name": "Scalable Neural Networks",
                        "venue_name": "IEEE Transactions on AI",
                        "published_at": "2023-05",
                        "publication_year": 2023
                    }
                ],
                "experience": {
                    "academic": [
                        {
                            "experience_type": "academic",
                            "institution": "Stanford University",
                            "role": "Postdoctoral Researcher",
                            "duration_years": 3.0
                        }
                    ],
                    "industry": [
                        {
                            "experience_type": "industry",
                            "organization": "Google Research",
                            "role": "Staff Scientist",
                            "duration_years": 4.0,
                            "location": "Mountain View, CA"
                        }
                    ]
                }
            })

        return json.dumps({
            "personal_information": {
                "full_name": "Dr. Jane Smith",
                "current_designation": "Senior Researcher",
                "email": "jane.smith@lab.org",
                "phone": "+1-555-0199"
            },
            "education": [
                {
                    "qualification_type": "PhD",
                    "degree": "PhD",
                    "stream": "Computer Science",
                    "university": "Stanford University",
                    "year": "2018",
                    "cgpa": "3.9"
                }
            ],
            "publications": [
                {
                    "publication_type": "journal",
                    "publication_name": "Scalable Neural Networks",
                    "venue_name": "IEEE Transactions on AI",
                    "published_at": "2023-05",
                    "publication_year": 2023
                }
            ],
            "experience": {
                "academic": [
                    {
                        "experience_type": "academic",
                        "institution": "Stanford University",
                        "role": "Postdoctoral Researcher",
                        "duration_years": 3.0
                    }
                ],
                "industry": [
                    {
                        "experience_type": "industry",
                        "organization": "Google Research",
                        "role": "Staff Scientist",
                        "duration_years": 4.0,
                        "location": "Mountain View, CA"
                    }
                ]
            }
        })


def test_scenario_1_small_resume_5k_tokens():
    mock_provider = MockLLMProvider()
    extractor = LLMExtractor(provider=mock_provider)
    
    # Generate 5k token text
    text_5k = "John Doe Resume\nExperience at Tech Corp.\n" + ("Publication research paper details. " * 500)
    
    res = extractor.extract_candidate_data(text_5k, candidate_id="CAND-5K")
    assert res is not None
    assert mock_provider.call_count == 1  # Exactly 1 LLM call


def test_scenario_2_safe_limit_15k_tokens():
    mock_provider = MockLLMProvider()
    extractor = LLMExtractor(provider=mock_provider)
    
    # Under default safe limit (12000 tokens) -> 1 call
    text_10k = "Candidate CV\n" + ("Academic research notes and publications. " * 1000)
    res = extractor.extract_candidate_data(text_10k, candidate_id="CAND-10K")
    assert res is not None
    assert mock_provider.call_count == 1


def test_scenario_3_and_4_and_5_recursive_splitting_large_resumes(monkeypatch):
    monkeypatch.setattr(settings, "SAFE_INPUT_TOKENS", 2000)
    monkeypatch.setattr(settings, "OVERLAP_TOKENS", 300)
    monkeypatch.setattr(settings, "CHUNK_CACHE_ENABLED", False)

    mock_provider = MockLLMProvider()
    extractor = LLMExtractor(provider=mock_provider)

    # Resume with ~6,000 tokens -> should split into multiple chunks
    large_resume = "SECTION: EDUCATION\nB.Tech at MIT 2015.\n\n" + ("WORK EXPERIENCE at BigCorp.\n" * 400) + "\n\nSECTION: PUBLICATIONS\n" + ("Paper on AI Systems.\n" * 400)
    
    res = extractor.extract_candidate_data(large_resume, candidate_id="CAND-LARGE")
    assert res is not None
    assert mock_provider.call_count > 1  # Multiple extraction calls + merge calls


def test_scenario_6_synthetic_100k_token_splitting(monkeypatch):
    monkeypatch.setattr(settings, "SAFE_INPUT_TOKENS", 1000)
    monkeypatch.setattr(settings, "OVERLAP_TOKENS", 200)

    token_counter = TokenCounter()
    splitter = RecursiveTextSplitter(token_counter=token_counter)

    synthetic_text = "SECTION 1: EXPERIENCE\n" + ("Heavy resume publication detail. " * 3000)
    chunks = splitter.split_text(synthetic_text, safe_limit=1000, overlap_tokens=200)
    
    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.token_count <= 1000  # Every leaf chunk strictly fits safe limit


def test_scenario_7_and_8_boundary_crossing_deduplication():
    mock_provider = MockLLMProvider()
    merger = HierarchicalMerger(provider=mock_provider)

    part1 = {
        "education": [{"degree": "B.Tech", "university": "XYZ University", "year": "2020"}],
        "experience": {"academic": [{"institution": "ABC Institute", "role": "Assistant Professor", "duration_years": 2.0}]}
    }
    part2 = {
        "education": [{"degree": "B.Tech", "university": "XYZ University", "cgpa": "8.7"}],
        "experience": {"academic": [{"institution": "ABC Institute", "role": "Assistant Professor", "duration_years": 2.0}]}
    }

    merged = merger.python_deterministic_merge(part1, part2)
    
    # Should consolidate into single education record with combined fields
    assert len(merged["education"]) == 1
    assert merged["education"][0]["degree"] == "B.Tech"
    assert merged["education"][0]["year"] == "2020"
    assert merged["education"][0]["cgpa"] == "8.7"
    
    # Should consolidate into single experience record
    assert len(merged["experience"]["academic"]) == 1


def test_scenario_9_overlapping_chunks_duplicate_publication():
    mock_provider = MockLLMProvider()
    merger = HierarchicalMerger(provider=mock_provider)

    part1 = {
        "publications": [{"publication_name": "Quantum Machine Learning", "venue_name": "Nature", "publication_year": 2023}]
    }
    part2 = {
        "publications": [{"publication_name": "Quantum Machine Learning", "venue_name": "Nature", "published_at": "2023-01"}]
    }

    merged = merger.python_deterministic_merge(part1, part2)
    assert len(merged["publications"]) == 1
    assert merged["publications"][0]["publication_name"] == "Quantum Machine Learning"
    assert merged["publications"][0]["publication_year"] == 2023
    assert merged["publications"][0]["published_at"] == "2023-01"


def test_scenario_10_malformed_json_repair():
    validator = JSONValidator()
    malformed = "```json\n{\n  'name': 'Test Candidate',\n  'education': [],\n}\n```"
    parsed = validator.parse_json(malformed)
    assert isinstance(parsed, dict)


def test_scenario_13_publication_classifier_malformed_json(tmp_path):
    cache_file = tmp_path / "pub_cache.json"
    pub_classifier = PublicationClassifier(cache_file=cache_file)
    
    # Test invalid string does not crash and defaults safely to Tier 3
    pub_classifier.provider = MockLLMProvider(default_response="MALFORMED { NOT JSON")
    res = pub_classifier.classify("Obscure Journal of Unknown Science")
    
    assert res["tier"] == "Tier 3"
    assert res["venue_name"] == "Obscure Journal of Unknown Science"
