import re
from typing import Dict, List, Optional, Any

# Hierarchy Ranks
DEGREE_RANKS: Dict[str, int] = {
    "PDF": 90,
    "Post Doctoral": 90,
    "PhD": 80,
    "Ph.D.": 80,
    "Doctor of Philosophy": 80,
    "PG": 70,
    "M.Tech": 70,
    "M.E.": 70,
    "M.Sc.": 70,
    "MCA": 70,
    "MBA": 70,
    "M.S.": 70,
    "UG": 60,
    "B.Tech": 60,
    "B.E.": 60,
    "B.Sc.": 60,
    "BCA": 60,
    "B.A.": 60,
    "Diploma": 50,
    "Other": 10
}

def normalize_degree_name(degree_raw: Optional[str]) -> str:
    if not degree_raw or not isinstance(degree_raw, str):
        return "Other"
    s = degree_raw.strip().lower()
    if not s:
        return "Other"

    if any(k in s for k in ["post doc", "postdoc", "post-doc", "pdf", "post doctoral"]):
        return "PDF"
    if any(k in s for k in ["ph.d", "phd", "doctor of philosophy", "doctorate"]):
        return "PhD"
    if any(k in s for k in ["m.tech", "mtech", "master of technology"]):
        return "M.Tech"
    if any(k in s for k in ["b.tech", "btech", "bachelor of technology"]):
        return "B.Tech"
    if any(k in s for k in ["m.e", "master of engineering"]):
        return "M.E."
    if any(k in s for k in ["b.e", "bachelor of engineering"]):
        return "B.E."
    if "mca" in s or "master of computer application" in s:
        return "MCA"
    if "bca" in s or "bachelor of computer application" in s:
        return "BCA"
    if any(k in s for k in ["m.sc", "msc", "master of science"]):
        return "M.Sc."
    if any(k in s for k in ["b.sc", "bsc", "bachelor of science"]):
        return "B.Sc."
    if "mba" in s:
        return "MBA"

    return "Other"

def get_degree_rank(degree_str: str) -> int:
    norm = normalize_degree_name(degree_str)
    return DEGREE_RANKS.get(norm, DEGREE_RANKS.get(degree_str, 10))

def matches_required_degree(required_degree: str, candidate_education: List[Dict[str, Any]]) -> tuple[bool, str]:
    if not required_degree or required_degree.strip().lower() == "none":
        return True, "No degree requirement specified"

    req_norm = normalize_degree_name(required_degree)
    req_rank = get_degree_rank(req_norm)

    candidate_degrees = []
    max_cand_rank = 0

    for item in candidate_education:
        deg = item.get("degree") or item.get("qualification_type") or ""
        norm_cand = normalize_degree_name(deg)
        rank = get_degree_rank(norm_cand)
        candidate_degrees.append(deg)
        if rank > max_cand_rank:
            max_cand_rank = rank

    if max_cand_rank >= req_rank and max_cand_rank > 10:
        return True, f"Candidate highest degree rank ({max_cand_rank}) meets or exceeds required '{required_degree}' rank ({req_rank})"

    return False, f"Required degree '{required_degree}' not found. Candidate degrees: {', '.join(candidate_degrees) if candidate_degrees else 'None'}"
