import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import settings
from backend.app.llm.extraction import LLMExtractor
from backend.app.llm.base import LLMProvider
from tests.test_adaptive_extraction import MockLLMProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestRunner")

def generate_synthetic_large_resume(candidate_id: str, approx_tokens: int) -> str:
    """
    Generate a realistic synthetic resume text with specified token count.
    """
    base_info = f"""
================================================================================
CURRICULUM VITAE - {candidate_id}
Dr. Alexander Montgomery, PhD
Email: alexander.montgomery.{candidate_id.lower()}@university.edu | Phone: +1 (555) 019-2834
Current Role: Chair of Computer Architecture & Distributed Systems

================================================================================
SECTION 1: EDUCATION & QUALIFICATIONS
--------------------------------------------------------------------------------
1. Doctor of Philosophy (Ph.D.) in Computer Science
   University of California, Berkeley (2012 - 2016)
   Dissertation: "Fault-Tolerant Distributed Consensus in Ultra-Scale Clusters"
   Advisor: Prof. David E. Culler | GPA: 4.0 / 4.0

2. Master of Science (M.S.) in Electrical Engineering & Computer Science
   Massachusetts Institute of Technology (MIT) (2010 - 2012)
   Thesis: "Low-Latency Hardware Accelerators for Graph Analytics"

3. Bachelor of Technology (B.Tech) in Computer Science & Engineering
   Indian Institute of Technology (IIT) Bombay (2006 - 2010)
   Graduated with Honors | Institute Gold Medalist
"""
    
    sections = [base_info]
    
    # Section 2: Academic & Industry Experience
    exp_block = """
================================================================================
SECTION 2: WORK & ACADEMIC EXPERIENCE
--------------------------------------------------------------------------------
[Academic Role] Professor & Department Head | Stanford University (2020 - Present)
- Directed the High-Performance Systems Laboratory supervising 18 PhD students.
- Secured $4.5M in NSF and DARPA research grants for resilient computing.
- Taught CS240 (Advanced Operating Systems) and CS348 (Distributed Databases).

[Academic Role] Associate Professor | Carnegie Mellon University (2016 - 2020)
- Led research initiatives in fault-tolerant memory architectures and RDMA networks.
- Published 24 peer-reviewed papers in top-tier conferences (ISCA, ASPLOS, OSDI).

[Industry Role] Principal Research Scientist | Google Research (2018 - 2020)
- Architected next-generation Spanner database query optimization algorithms.
- Reduced p99 tail latencies across global data center clusters by 18.4%.
"""
    sections.append(exp_block)

    # Section 3: Publications & Patents
    pub_template = """
[Publication {i}] "{title}"
Authors: Alexander Montgomery, {coauthors}
Venue: {venue} ({year})
Abstract: This paper presents a novel algorithmic framework for high-throughput zero-copy RPC mechanisms over Converged Ethernet (RoCEv2). We evaluate our prototype across a 10,000-node cluster and demonstrate a 4.2x speedup in transaction throughput compared to baseline MPI implementations.
"""
    
    venues = [
        "IEEE Transactions on Parallel and Distributed Systems",
        "ACM Symposium on Operating Systems Principles (SOSP)",
        "USENIX Symposium on Operating Systems Design and Implementation (OSDI)",
        "IEEE International Symposium on Computer Architecture (ISCA)",
        "ACM SIGCOMM",
        "IEEE Micro"
    ]

    pubs_block = ["\n================================================================================\nSECTION 3: PUBLICATIONS AND PATENTS\n--------------------------------------------------------------------------------"]
    i = 1
    while True:
        p_text = pub_template.format(
            i=i,
            title=f"Scalable Resilience Protocol for Exascale Computing Systems Part {i}",
            coauthors=f"Co-author A{i}, Co-author B{i}, Co-author C{i}",
            venue=venues[i % len(venues)],
            year=2015 + (i % 10)
        )
        pubs_block.append(p_text)
        current_text = "\n".join(sections) + "\n".join(pubs_block)
        # Check token length approximation
        estimated_tokens = int(len(current_text) / 3.8)
        if estimated_tokens >= approx_tokens:
            break
        i += 1

    sections.append("\n".join(pubs_block))
    return "\n".join(sections)

def test_large_candidate(candidate_id: str, target_tokens: int, provider: LLMProvider):
    print("\n" + "=" * 80)
    print(f"TESTING ADAPTIVE RECURSIVE EXTRACTION FOR {candidate_id} (~{target_tokens} tokens)")
    print("=" * 80)

    # Create synthetic resume
    text = generate_synthetic_large_resume(candidate_id, target_tokens)
    
    extractor = LLMExtractor(provider=provider)
    result = extractor.extract_candidate_data(text, candidate_id=candidate_id)

    print(f"\n---> {candidate_id} EXTRACTION SUCCESSFUL!")
    print(f"Extracted Full Name: {result.get('personal_information', {}).get('full_name')}")
    print(f"Education Count: {len(result.get('education', []))}")
    print(f"Publications Count: {len(result.get('publications', []))}")
    print(f"Academic Experience Count: {len(result.get('experience', {}).get('academic', []))}")
    print(f"Industry Experience Count: {len(result.get('experience', {}).get('industry', []))}")
    print("=" * 80)

if __name__ == "__main__":
    mock_provider = MockLLMProvider()
    
    # Test CAND-0018 (approx 65,000 tokens)
    test_large_candidate("CAND-0018", target_tokens=65000, provider=mock_provider)
    
    # Test CAND-0039 (approx 80,000 tokens)
    test_large_candidate("CAND-0039", target_tokens=80000, provider=mock_provider)
