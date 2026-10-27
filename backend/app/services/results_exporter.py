import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from backend.app.config import settings
from backend.app.schemas.candidate import is_secondary_education

logger = logging.getLogger("ResultsExporter")

class ResultsExporter:
    """
    Exports clean, human-readable session results into the project-root `results/` folder.
    Each session gets a dedicated folder: `results/<session_id>/`
    
    Files generated:
    1. llm_extracted_outputs.json     : Raw & structured text extraction output from LLM per candidate.
    2. university_classifications.json: Detailed University/Institution tier classifications.
    3. experience_classifications.json: Detailed Academic & Industry experience classifications & scores.
    4. publication_classifications.json: Detailed Publication venue tier classifications & window filtering.
    5. shortlisting_and_top2_result.json: Complete shortlisting matrix & top 2 shortlist evaluation.
    6. shortlisting_and_top2_result.md  : Markdown report detailing how top 2 candidates were selected.
    """

    @staticmethod
    def export_session_results(session_meta: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Path:
        session_id = session_meta.get("session_id", "SES-UNKNOWN")
        session_results_dir = settings.RESULTS_DIR / session_id
        session_results_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting session results for {session_id} to {session_results_dir}")

        # 1. LLM Extracted Outputs per candidate
        extracted_data = {
            "session_id": session_id,
            "job_title": session_meta.get("job_title"),
            "total_candidates": len(candidates),
            "candidates_llm_extracted_data": []
        }
        for cand in candidates:
            p_info = cand.get("personal_information", {})
            extracted_data["candidates_llm_extracted_data"].append({
                "candidate_id": cand.get("candidate_id"),
                "source_file": cand.get("source_file"),
                "candidate_name": p_info.get("full_name"),
                "email": p_info.get("email"),
                "phone": p_info.get("phone"),
                "current_designation": p_info.get("current_designation"),
                "extracted_education": cand.get("education", []),
                "extracted_experience": cand.get("experience", {}),
                "extracted_publications": cand.get("publications", [])
            })

        (session_results_dir / "llm_extracted_outputs.json").write_text(
            json.dumps(extracted_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 2. University Classifications by LLM
        uni_data = {
            "session_id": session_id,
            "total_candidates": len(candidates),
            "university_classifications_by_candidate": []
        }
        for cand in candidates:
            p_info = cand.get("personal_information", {})
            edu_items = []
            for edu in cand.get("education", []):
                inst = edu.get("university") or edu.get("institution") or "Unknown"
                deg_name = edu.get("degree")
                if is_secondary_education(deg_name, edu.get("qualification_type")):
                    tier = None
                    score = None
                else:
                    tier = edu.get("institution_tier") or "Tier 3"
                    score = edu.get("institution_score") if edu.get("institution_score") is not None else settings.TIER_3_SCORE
                edu_items.append({
                    "degree": deg_name,
                    "specialization": edu.get("specialization") or edu.get("stream"),
                    "institution": inst,
                    "classified_tier": tier,
                    "tier_score": score,
                    "year_of_completion": edu.get("year_of_completion") or edu.get("year")
                })
            
            acad_exp_unis = []
            exp_cand = cand.get("experience", [])
            if isinstance(exp_cand, list):
                acad_exp = [a for a in exp_cand if isinstance(a, dict) and a.get("experience_type") == "academic"]
            elif isinstance(exp_cand, dict):
                acad_exp = exp_cand.get("academic", [])
            else:
                acad_exp = []

            for a in acad_exp:
                inst = a.get("institution") or "Unknown"
                tier = a.get("institution_tier", "Tier 3")
                score = a.get("institution_score", settings.TIER_3_SCORE)
                acad_exp_unis.append({
                    "designation": a.get("role") or a.get("designation"),
                    "institution": inst,
                    "classified_tier": tier,
                    "tier_score": score,
                    "duration_years": a.get("duration_years")
                })

            uni_data["university_classifications_by_candidate"].append({
                "candidate_id": cand.get("candidate_id"),
                "candidate_name": p_info.get("full_name"),
                "education_degrees": edu_items,
                "academic_experience_institutions": acad_exp_unis
            })

        (session_results_dir / "university_classifications.json").write_text(
            json.dumps(uni_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 3. Experience Classifications by LLM
        exp_data = {
            "session_id": session_id,
            "total_candidates": len(candidates),
            "experience_classifications_by_candidate": []
        }
        for cand in candidates:
            p_info = cand.get("personal_information", {})
            cand_exp = cand.get("experience", [])
            shortlisting = cand.get("shortlisting", {})
            
            if isinstance(cand_exp, list):
                acad_raw = [a for a in cand_exp if isinstance(a, dict) and a.get("experience_type") == "academic"]
                ind_raw = [i for i in cand_exp if isinstance(i, dict) and i.get("experience_type") in ("professional", "industry")]
            elif isinstance(cand_exp, dict):
                acad_raw = cand_exp.get("academic", [])
                ind_raw = cand_exp.get("industry", []) or cand_exp.get("professional", [])
            else:
                acad_raw, ind_raw = [], []

            acad_list = []
            total_acad_years = 0.0
            for a in acad_raw:
                yrs = float(a.get("duration_years") or 0.0)
                total_acad_years += yrs
                role_nm = a.get("role") or a.get("designation") or a.get("job_title") or "Role N/A"
                inst_nm = a.get("institution") or a.get("company_name") or a.get("company") or "Institution"
                acad_list.append({
                    "designation": role_nm,
                    "institution": inst_nm,
                    "start_date": a.get("start_date"),
                    "end_date": a.get("end_date"),
                    "duration_years": yrs,
                    "is_current": a.get("is_current", False),
                    "is_internship": a.get("is_internship", False),
                    "institution_tier": a.get("institution_tier", "Tier 3"),
                    "institution_score": a.get("institution_score", settings.TIER_3_SCORE)
                })

            ind_list = []
            total_ind_years = 0.0
            for i in ind_raw:
                yrs = float(i.get("duration_years") or 0.0)
                total_ind_years += yrs
                role_nm = i.get("role") or i.get("designation") or i.get("job_title") or "Role N/A"
                comp_nm = i.get("institution") or i.get("company") or i.get("organization") or i.get("company_name") or "Company"
                ind_list.append({
                    "designation": role_nm,
                    "company": comp_nm,
                    "start_date": i.get("start_date"),
                    "end_date": i.get("end_date"),
                    "duration_years": yrs,
                    "is_current": i.get("is_current", False),
                    "is_internship": i.get("is_internship", False),
                    "location": i.get("location")
                })

            total_exp = cand.get("total_experience")
            if total_exp is None or total_exp == 0.0:
                if isinstance(cand_exp, dict):
                    total_exp = cand_exp.get("calculated_total_years")
                if total_exp is None or total_exp == 0.0:
                    total_exp = round(total_acad_years + total_ind_years, 2)
                    if total_exp == 0.0 and isinstance(cand_exp, dict) and cand_exp.get("explicitly_mentioned_years"):
                        total_exp = cand_exp["explicitly_mentioned_years"]

            exp_data["experience_classifications_by_candidate"].append({
                "candidate_id": cand.get("candidate_id"),
                "candidate_name": p_info.get("full_name"),
                "total_academic_experience_years": round(total_acad_years, 2),
                "total_industry_experience_years": round(total_ind_years, 2),
                "total_experience_years": round(total_exp, 2),
                "explicitly_mentioned_years": exp.get("explicitly_mentioned_years"),
                "calculated_total_years": exp.get("calculated_total_years"),
                "calculation_basis": exp.get("calculation_basis", "calculated_from_history"),
                "experience_status": exp.get("experience_status", "available"),
                "discrepancy_note": exp.get("discrepancy_note"),
                "academic_experience_score": shortlisting.get("academic_experience_score"),
                "industry_experience_score": shortlisting.get("industry_experience_score"),
                "academic_experiences": acad_list,
                "industry_experiences": ind_list
            })

        (session_results_dir / "experience_classifications.json").write_text(
            json.dumps(exp_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 4. Publication Classifications by LLM
        pub_data = {
            "session_id": session_id,
            "total_candidates": len(candidates),
            "publication_classifications_by_candidate": []
        }
        for cand in candidates:
            p_info = cand.get("personal_information", {})
            pubs = cand.get("publications", [])
            shortlisting = cand.get("shortlisting", {})

            pub_list = []
            for p in pubs:
                venue = p.get("venue_name") or p.get("publisher") or "Unknown"
                tier = p.get("venue_tier", "Tier 3")
                score = p.get("venue_score", settings.TIER_3_SCORE)
                pub_list.append({
                    "title": p.get("title"),
                    "venue_name": venue,
                    "classified_tier": tier,
                    "venue_score": score,
                    "year": p.get("year"),
                    "in_publication_window": p.get("in_window", True)
                })

            pub_data["publication_classifications_by_candidate"].append({
                "candidate_id": cand.get("candidate_id"),
                "candidate_name": p_info.get("full_name"),
                "total_publications_evaluated": len(pub_list),
                "publication_score": shortlisting.get("publication_score"),
                "publications": pub_list
            })

        (session_results_dir / "publication_classifications.json").write_text(
            json.dumps(pub_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 5. Shortlisting Result & Top 2 Selection Explanation (JSON & MD)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                1 if c.get("shortlisting", {}).get("shortlisted") else 0,
                c.get("shortlisting", {}).get("final_score", 0.0)
            ),
            reverse=True
        )

        shortlist_data = {
            "session_id": session_id,
            "job_meta": {
                "job_title": session_meta.get("job_title"),
                "required_degree": session_meta.get("required_degree"),
                "required_specialization": session_meta.get("required_specialization"),
                "minimum_experience_years": session_meta.get("minimum_experience"),
                "minimum_publications": session_meta.get("minimum_publications"),
                "publication_window_years": session_meta.get("publication_window_years"),
                "top_n_requested": session_meta.get("top_n", 2),
                "scoring_weights": session_meta.get("scoring_weights")
            },
            "top_shortlisted_candidates": [
                {
                    "rank": cand.get("shortlisting", {}).get("rank"),
                    "candidate_id": cand.get("candidate_id"),
                    "candidate_name": cand.get("personal_information", {}).get("full_name"),
                    "final_score": cand.get("shortlisting", {}).get("final_score"),
                    "eligible": cand.get("shortlisting", {}).get("eligible"),
                    "component_scores": {
                        "education_score": cand.get("shortlisting", {}).get("education_score"),
                        "publication_score": cand.get("shortlisting", {}).get("publication_score"),
                        "academic_experience_score": cand.get("shortlisting", {}).get("academic_experience_score"),
                        "industry_experience_score": cand.get("shortlisting", {}).get("industry_experience_score")
                    }
                }
                for cand in sorted_candidates if cand.get("shortlisting", {}).get("shortlisted")
            ],
            "all_evaluated_candidates": [
                {
                    "rank": cand.get("shortlisting", {}).get("rank"),
                    "candidate_id": cand.get("candidate_id"),
                    "candidate_name": cand.get("personal_information", {}).get("full_name"),
                    "eligible": cand.get("shortlisting", {}).get("eligible"),
                    "shortlisted": cand.get("shortlisting", {}).get("shortlisted"),
                    "final_score": cand.get("shortlisting", {}).get("final_score"),
                    "reasons": cand.get("shortlisting", {}).get("reasons", [])
                }
                for cand in sorted_candidates
            ]
        }

        (session_results_dir / "shortlisting_and_top2_result.json").write_text(
            json.dumps(shortlist_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Write Human-Readable Markdown Report on How Top 2 are listed
        top2 = [c for c in sorted_candidates if c.get("shortlisting", {}).get("shortlisted")][:2]
        md_lines = [
            f"# Session Shortlisting & Ranking Report: {session_id}",
            f"**Job Title:** {session_meta.get('job_title')}",
            f"**Requirements:** {session_meta.get('required_degree')} in {session_meta.get('required_specialization')} | "
            f"Min Experience: {session_meta.get('minimum_experience')} yrs | Min Pubs: {session_meta.get('minimum_publications')}",
            f"**Scoring Weights:** {json.dumps(session_meta.get('scoring_weights', {}))}",
            "",
            "## How Top 2 Candidates Were Selected & Listed",
            "The top candidates are shortlisted based on a 2-stage process:",
            "1. **Strict Eligibility Filtering**: Candidates must meet degree requirements, specialization matching, minimum total experience, and minimum recent publications within the window.",
            "2. **Weighted Scoring**: Eligible candidates are scored on Education Tier, Publication Tier, Academic Experience Tier, and Industry Experience Tier, combined via weighted sum into a Final Weighted Score (0 to 100).",
            "",
            "### Top 2 Shortlisted Candidates Breakdown:",
            ""
        ]

        if top2:
            for idx, cand in enumerate(top2, 1):
                p_info = cand.get("personal_information", {})
                sl = cand.get("shortlisting", {})
                md_lines.extend([
                    f"### Rank #{sl.get('rank', idx)}: {p_info.get('full_name')} (ID: {cand.get('candidate_id')})",
                    f"- **Final Weighted Score:** `{sl.get('final_score', 0.0):.2f} / 100`",
                    f"- **Eligibility Status:** {'✅ Eligible' if sl.get('eligible') else '❌ Ineligible'}",
                    f"- **Education Score:** `{float(sl.get('education_score', 0))*100:.1f}%`",
                    f"- **Publication Score:** `{float(sl.get('publication_score', 0))*100:.1f}%`",
                    f"- **Academic Exp Score:** `{float(sl.get('academic_experience_score', 0))*100:.1f}%`",
                    f"- **Industry Exp Score:** `{float(sl.get('industry_experience_score', 0))*100:.1f}%`",
                    f"- **Why Selected:** Higher Tier 1/2 university degree, publication count in recognized venues, and total qualifying experience.",
                    ""
                ])
        else:
            md_lines.append("*No candidates met the minimum eligibility threshold for shortlisting.*")

        md_lines.extend([
            "## All Candidates Summary Table",
            "| Rank | Candidate ID | Name | Eligible | Shortlisted | Final Score | Flags / Reasons |",
            "|------|--------------|------|----------|-------------|-------------|-----------------|"
        ])

        for cand in sorted_candidates:
            sl = cand.get("shortlisting", {})
            p_info = cand.get("personal_information", {})
            rk = sl.get("rank") or "-"
            cid = cand.get("candidate_id")
            nm = p_info.get("full_name") or "Unknown"
            el = "Yes" if sl.get("eligible") else "No"
            sh = "Yes" if sl.get("shortlisted") else "No"
            sc = f"{sl.get('final_score', 0.0):.2f}"
            reasons_str = "; ".join(sl.get("reasons", [])) or "None"
            md_lines.append(f"| {rk} | {cid} | {nm} | {el} | {sh} | {sc} | {reasons_str} |")

        (session_results_dir / "shortlisting_and_top2_result.md").write_text(
            "\n".join(md_lines), encoding="utf-8"
        )

        return session_results_dir
