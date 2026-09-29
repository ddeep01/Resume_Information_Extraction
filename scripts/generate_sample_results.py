import sys
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings
from backend.app.services.results_exporter import ResultsExporter

def run_sample_export():
    session_meta = {
        "session_id": "SES-2026-0001",
        "job_title": "Assistant Professor - Artificial Intelligence & Systems",
        "required_degree": "Ph.D.",
        "required_specialization": "Computer Science & Artificial Intelligence",
        "minimum_experience": 3.0,
        "minimum_publications": 3,
        "publication_window_years": 5,
        "top_n": 2,
        "scoring_weights": {
            "education": 0.30,
            "publications": 0.30,
            "academic_experience": 0.25,
            "industry_experience": 0.15
        }
    }

    sample_candidates = [
        {
            "candidate_id": "CAND-0001",
            "source_file": "Dr_Alexander_Montgomery_Resume.pdf",
            "personal_information": {
                "full_name": "Dr. Alexander Montgomery",
                "email": "alexander.montgomery@berkeley.edu",
                "phone": "+1 (555) 019-2834",
                "current_designation": "Chair of Computer Architecture & Distributed Systems"
            },
            "education": [
                {
                    "degree": "Ph.D.",
                    "specialization": "Computer Science",
                    "university": "University of California, Berkeley",
                    "institution_tier": "Tier 1",
                    "institution_score": 1.0,
                    "year_of_completion": 2016
                },
                {
                    "degree": "M.S.",
                    "specialization": "Electrical Engineering & Computer Science",
                    "university": "Massachusetts Institute of Technology (MIT)",
                    "institution_tier": "Tier 1",
                    "institution_score": 1.0,
                    "year_of_completion": 2012
                },
                {
                    "degree": "B.Tech",
                    "specialization": "Computer Science & Engineering",
                    "university": "IIT Bombay",
                    "institution_tier": "Tier 1",
                    "institution_score": 1.0,
                    "year_of_completion": 2010
                }
            ],
            "publications": [
                {
                    "title": "Fault-Tolerant Consensus Protocols in Distributed Exascale Memory",
                    "venue_name": "ACM Symposium on Operating Systems Principles (SOSP)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2023,
                    "in_window": True
                },
                {
                    "title": "Low-Latency RDMA Networks for Ultra-Scale Graph Analytics",
                    "venue_name": "USENIX Symposium on Operating Systems Design and Implementation (OSDI)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2022,
                    "in_window": True
                },
                {
                    "title": "Scalable Hardware Acceleration for Deep Neural Inference",
                    "venue_name": "IEEE International Symposium on Computer Architecture (ISCA)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2021,
                    "in_window": True
                },
                {
                    "title": "High-Throughput RPC Mechanisms over Converged Ethernet",
                    "venue_name": "IEEE Transactions on Parallel and Distributed Systems",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2020,
                    "in_window": True
                }
            ],
            "experience": {
                "academic": [
                    {
                        "designation": "Professor & Department Head",
                        "institution": "Stanford University",
                        "duration_years": 4.0,
                        "institution_tier": "Tier 1",
                        "institution_score": 1.0
                    },
                    {
                        "designation": "Associate Professor",
                        "institution": "Carnegie Mellon University",
                        "duration_years": 4.0,
                        "institution_tier": "Tier 1",
                        "institution_score": 1.0
                    }
                ],
                "industry": [
                    {
                        "designation": "Principal Research Scientist",
                        "company": "Google Research",
                        "duration_years": 2.0
                    }
                ]
            },
            "shortlisting": {
                "eligible": True,
                "shortlisted": True,
                "education_score": 1.0,
                "publication_score": 1.0,
                "academic_experience_score": 1.0,
                "industry_experience_score": 0.40,
                "final_score": 91.0,
                "rank": 1,
                "reasons": []
            }
        },
        {
            "candidate_id": "CAND-0002",
            "source_file": "Dr_Sophia_Chen_Resume.pdf",
            "personal_information": {
                "full_name": "Dr. Sophia Chen",
                "email": "sophia.chen@cs.cmu.edu",
                "phone": "+1 (555) 392-1049",
                "current_designation": "Senior AI Systems Scientist"
            },
            "education": [
                {
                    "degree": "Ph.D.",
                    "specialization": "Artificial Intelligence & Machine Learning",
                    "university": "Carnegie Mellon University",
                    "institution_tier": "Tier 1",
                    "institution_score": 1.0,
                    "year_of_completion": 2018
                },
                {
                    "degree": "B.S.",
                    "specialization": "Computer Science",
                    "university": "Cornell University",
                    "institution_tier": "Tier 1",
                    "institution_score": 1.0,
                    "year_of_completion": 2013
                }
            ],
            "publications": [
                {
                    "title": "Transformer Attention Optimization for Edge Computing",
                    "venue_name": "Conference on Neural Information Processing Systems (NeurIPS)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2023,
                    "in_window": True
                },
                {
                    "title": "Generative Diffusion Models for High-Dimensional Time Series",
                    "venue_name": "International Conference on Machine Learning (ICML)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2022,
                    "in_window": True
                },
                {
                    "title": "Self-Supervised Representation Learning on Knowledge Graphs",
                    "venue_name": "International Conference on Learning Representations (ICLR)",
                    "venue_tier": "Tier 1",
                    "venue_score": 1.0,
                    "year": 2021,
                    "in_window": True
                }
            ],
            "experience": {
                "academic": [
                    {
                        "designation": "Assistant Professor",
                        "institution": "University of Washington",
                        "duration_years": 3.5,
                        "institution_tier": "Tier 1",
                        "institution_score": 1.0
                    }
                ],
                "industry": [
                    {
                        "designation": "Senior Research Scientist",
                        "company": "FAIR (Meta AI)",
                        "duration_years": 2.5
                    }
                ]
            },
            "shortlisting": {
                "eligible": True,
                "shortlisted": True,
                "education_score": 1.0,
                "publication_score": 1.0,
                "academic_experience_score": 0.70,
                "industry_experience_score": 0.50,
                "final_score": 82.5,
                "rank": 2,
                "reasons": []
            }
        },
        {
            "candidate_id": "CAND-0003",
            "source_file": "Rahul_Sharma_Resume.pdf",
            "personal_information": {
                "full_name": "Rahul Sharma",
                "email": "rahul.sharma@techcorp.com",
                "phone": "+91 98765 43210",
                "current_designation": "Senior Software Engineer"
            },
            "education": [
                {
                    "degree": "B.Tech",
                    "specialization": "Computer Science",
                    "university": "State Engineering College",
                    "institution_tier": "Tier 3",
                    "institution_score": 0.33,
                    "year_of_completion": 2019
                }
            ],
            "publications": [
                {
                    "title": "Web Application Optimization Strategies",
                    "venue_name": "Regional Tech Journal",
                    "venue_tier": "Tier 3",
                    "venue_score": 0.33,
                    "year": 2022,
                    "in_window": True
                }
            ],
            "experience": {
                "academic": [],
                "industry": [
                    {
                        "designation": "Software Engineer",
                        "company": "TechCorp",
                        "duration_years": 4.0
                    }
                ]
            },
            "shortlisting": {
                "eligible": False,
                "shortlisted": False,
                "education_score": 0.33,
                "publication_score": 0.33,
                "academic_experience_score": 0.0,
                "industry_experience_score": 0.80,
                "final_score": 31.9,
                "rank": 3,
                "reasons": [
                    "Missing required Ph.D. degree",
                    "Specialization mismatch (expected AI & Systems)",
                    "Insufficient publications (1 / 3 required)"
                ]
            }
        }
    ]

    out_dir = ResultsExporter.export_session_results(session_meta, sample_candidates)
    print(f"\n[SUCCESS] Exported session results to: {out_dir}")

if __name__ == "__main__":
    run_sample_export()
