from datetime import datetime
from typing import Dict, Any, List
from backend.app.shortlisting.degree_matcher import matches_required_degree
from backend.app.shortlisting.specialization_matcher import matches_specialization

def filter_publications_by_window(publications: List[Dict[str, Any]], window_years: int, current_year: int = None) -> List[Dict[str, Any]]:
    if current_year is None:
        current_year = datetime.now().year

    min_year = current_year - window_years
    valid_pubs = []
    for pub in publications:
        year = pub.get("publication_year")
        if not year and pub.get("published_at"):
            # Try to extract 4 digit year
            try:
                import re
                m = re.search(r"\b(19|20)\d{2}\b", str(pub["published_at"]))
                if m:
                    year = int(m.group(0))
            except Exception:
                pass

        if year and isinstance(year, int):
            if year >= min_year:
                pub["in_publication_window"] = True
                valid_pubs.append(pub)
            else:
                pub["in_publication_window"] = False
        else:
            # If date missing, include by default but mark
            pub["in_publication_window"] = True
            valid_pubs.append(pub)

    return valid_pubs

def evaluate_candidate_eligibility(
    candidate_data: Dict[str, Any],
    required_degree: str,
    required_specialization: str,
    minimum_experience: float,
    minimum_publications: int,
    publication_window_years: int
) -> tuple[bool, List[str], List[Dict[str, Any]], float]:
    """
    Evaluates candidate eligibility based on recruiter session requirements.
    Returns: (eligible: bool, reasons: List[str], filtered_publications: List[Dict], total_experience: float)
    """
    reasons = []
    is_eligible = True

    # 1. Degree Evaluation
    education_list = candidate_data.get("education", [])
    degree_ok, degree_reason = matches_required_degree(required_degree, education_list)
    reasons.append(degree_reason)
    if not degree_ok:
        is_eligible = False

    # 2. Specialization Evaluation
    streams = [item.get("stream") or "" for item in education_list if item.get("stream")]
    spec_ok, spec_reason = matches_specialization(required_specialization, streams)
    reasons.append(spec_reason)
    if not spec_ok:
        is_eligible = False

    # 3. Experience Evaluation (Academic + Industry)
    exp = candidate_data.get("experience", {})
    acad_exp_list = exp.get("academic", [])
    ind_exp_list = exp.get("industry", [])

    total_acad_years = sum(float(item.get("duration_years") or 0.0) for item in acad_exp_list)
    total_ind_years = sum(float(item.get("duration_years") or 0.0) for item in ind_exp_list)
    total_relevant_exp = round(total_acad_years + total_ind_years, 2)

    if total_relevant_exp >= minimum_experience:
        reasons.append(f"Minimum experience met: candidate has {total_relevant_exp} yrs relevant experience (Academic: {total_acad_years} yrs, Industry: {total_ind_years} yrs) vs required {minimum_experience} yrs")
    else:
        is_eligible = False
        reasons.append(f"Minimum experience NOT met: candidate has {total_relevant_exp} yrs relevant experience vs required {minimum_experience} yrs")

    # 4. Publication Evaluation within Window
    pubs = candidate_data.get("publications", [])
    window_pubs = filter_publications_by_window(pubs, publication_window_years)
    relevant_pub_count = len(window_pubs)

    if relevant_pub_count >= minimum_publications:
        reasons.append(f"Publication criteria met: {relevant_pub_count} publications within the last {publication_window_years} years vs required {minimum_publications}")
    else:
        is_eligible = False
        reasons.append(f"Publication criteria NOT met: {relevant_pub_count} publications within the last {publication_window_years} years vs required {minimum_publications}")

    return is_eligible, reasons, window_pubs, total_relevant_exp
