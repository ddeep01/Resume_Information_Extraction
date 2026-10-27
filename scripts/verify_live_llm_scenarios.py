"""
Live Verification Script with Local Ollama (llama3.2).
Tests representative resume scenarios end-to-end through LLMExtractor.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.llm.extraction import LLMExtractor

def run_live_tests():
    print("Initializing LLMExtractor with local Ollama provider...")
    extractor = LLMExtractor()
    print("Provider initialized successfully.\n")

    test_resumes = {
        "scenario_01_explicit_10_years": """
        SARAH JENKINS
        Email: sarah.jenkins@techcorp.io | Phone: +1 415 555 0192
        San Francisco, CA

        PROFESSIONAL SUMMARY
        Distinguished Cloud Architect with over 10 years of experience designing and scaling cloud native platforms.

        WORK EXPERIENCE
        Principal Architect | CloudScale Inc.
        January 2018 - Present | San Francisco, CA
        - Led global cloud migration across 4 regions.

        Senior DevOps Engineer | NexaCorp
        June 2013 - December 2017 | Austin, TX
        - Designed CI/CD infrastructure reducing deployment time by 80%.

        EDUCATION
        B.S. in Computer Science | University of California, Berkeley | 2013
        """,

        "scenario_03_calculated_from_history_no_explicit": """
        ROBERT CHEN
        Email: robert.chen@devmail.com | Phone: +1 650 555 8392
        Seattle, WA

        WORK EXPERIENCE
        Software Developer | ABC Technologies
        January 2016 - December 2019 | Seattle, WA
        - Developed distributed backend services in Go.

        Senior Software Developer | XYZ Solutions
        January 2020 - December 2022 | Redmond, WA
        - Led core architecture of real-time telemetry processing pipeline.

        Technical Lead | PQR Technologies
        January 2023 - Present | Bellevue, WA
        - Directing engineering operations and system scalability.

        EDUCATION
        Bachelor of Engineering in Computer Science | University of Washington | 2015
        """,

        "scenario_05_overlapping_employment": """
        EMILY WATSON
        Email: emily.watson@enterprise.com
        New York, NY

        PROFESSIONAL SUMMARY
        Senior Software Engineer specializing in financial technologies.

        EXPERIENCE
        Senior Engineer | Alpha Capital
        January 2018 - December 2020 | New York, NY
        - High-frequency order routing engine development.

        Technical Consultant | Beta Global Advisors
        January 2020 - December 2022 | New York, NY
        - Architectural consulting on distributed ledger integrations.

        EDUCATION
        B.S. in Information Systems | Columbia University | 2017
        """,

        "scenario_09_undated_employment": """
        MICHAEL T. VAUGHN
        Email: mvaughn@sample.org
        Chicago, IL

        WORK EXPERIENCE
        Software Engineer at ABC Technologies
        Chicago, IL
        - Maintained enterprise resource planning database modules.

        EDUCATION
        B.S. in Computer Engineering | University of Illinois Chicago | 2019
        """,

        "scenario_14_fresh_graduate_no_experience": """
        ANANYA SHARMA
        Email: ananya.sharma@campus.edu | Phone: +91 9820011223
        Bangalore, India

        CAREER OBJECTIVE
        Enthusiastic and hardworking Computer Science graduate looking to begin a professional career in software development.

        EDUCATION
        Bachelor of Technology in Computer Science | National Institute of Technology Karnataka | 2024 | CGPA: 9.2

        ACADEMIC PROJECTS
        - Automated Healthcare Diagnostics: Built a deep learning model for skin lesion classification using PyTorch.
        - Campus Room Booking Portal: Full stack web portal using FastAPI and React.

        TECHNICAL SKILLS
        Python, C++, Java, PyTorch, React, PostgreSQL, Docker, Git
        """
    }

    results = {}
    for scenario_name, resume_text in test_resumes.items():
        print(f"==================================================", flush=True)
        print(f"Executing: {scenario_name}", flush=True)
        print(f"==================================================", flush=True)
        try:
            extracted = extractor.extract_candidate_data(resume_text, candidate_id=scenario_name)
            exp = extracted.get("experience", {})
            print(f"Candidate Name: {extracted.get('personal_information', {}).get('full_name')}", flush=True)
            print(f"Explicit Years: {exp.get('explicitly_mentioned_years')}", flush=True)
            print(f"Calculated Total Years: {exp.get('calculated_total_years')}", flush=True)
            print(f"Calculation Basis: {exp.get('calculation_basis')}", flush=True)
            print(f"Experience Status: {exp.get('experience_status')}", flush=True)
            print(f"Discrepancy Note: {exp.get('discrepancy_note')}", flush=True)
            print(f"Records Count: Academic={len(exp.get('academic', []))}, Industry={len(exp.get('industry', []))}", flush=True)
            for idx, item in enumerate(exp.get("industry", [])):
                print(f"  Record {idx+1}: {item.get('role')} at {item.get('company_name')} | {item.get('start_date')} - {item.get('end_date')} ({item.get('duration_years')} yrs) | Current={item.get('is_current')}", flush=True)
            
            results[scenario_name] = extracted
        except Exception as e:
            print(f"FAILED {scenario_name}: {e}", flush=True)
            import traceback
            traceback.print_exc()

    # Save output for inspection
    output_path = Path("scratch") / "live_llm_test_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll live results saved to: {output_path}")

if __name__ == "__main__":
    run_live_tests()
