"""
==============================================================================
Degree Normalizer & Standardization System
==============================================================================

Purpose
-------
Normalize raw degree strings extracted from resumes into canonical degree
categories without modifying original raw degree text.

Canonical Categories:
- Ph.D.
- Post Doctoral
- M.Tech
- B.Tech
- M.E.
- B.E.
- M.Sc.
- B.Sc.
- MCA
- BCA
- MBA
- M.A.
- B.A.
- M.Phil.
- M.S.
- B.Ed
- Diploma
- Higher Secondary (12th)
- Secondary (10th)
- Other
==============================================================================
"""

import re
from typing import Dict, Any, List, Optional

# Degree Hierarchy Rank (Highest to Lowest)
DEGREE_HIERARCHY: Dict[str, int] = {
    "Post Doctoral": 90,
    "Ph.D.": 80,
    "M.Tech": 70,
    "M.E.": 70,
    "M.Sc.": 70,
    "MCA": 70,
    "MBA": 70,
    "M.A.": 70,
    "M.Phil.": 70,
    "M.S.": 70,
    "B.Tech": 60,
    "B.E.": 60,
    "B.Sc.": 60,
    "BCA": 60,
    "B.A.": 60,
    "B.Ed": 60,
    "Diploma": 50,
    "Higher Secondary (12th)": 40,
    "Secondary (10th)": 30,
    "Other": 10
}


def normalize_degree(degree_raw: Optional[str]) -> str:
    """
    Map a raw degree string to its canonical degree category.
    Does not mutate the raw degree input string.
    """
    if not degree_raw or not isinstance(degree_raw, str):
        return "Other"

    s = degree_raw.strip()
    if not s:
        return "Other"

    s_lower = s.lower()

    # 1. Post Doctoral / Postdoc
    if any(pattern in s_lower for pattern in [
        "post doc", "postdoc", "post-doc", "post doctoral"
    ]):
        return "Post Doctoral"

    # 2. Ph.D. / Doctor of Philosophy / Doctorate / Dr. of Philosophy
    if any(pattern in s_lower for pattern in [
        "ph.d", "phd", "doctor of philosophy", "doctorate", "dr. of philosophy", "ph. d"
    ]):
        return "Ph.D."

    # 3. M.Tech / Master of Technology / Masters in Technology
    if any(pattern in s_lower for pattern in [
        "m.tech", "mtech", "m. tech", "master of technology", "masters in technology"
    ]):
        return "M.Tech"

    # 4. B.Tech / Bachelor of Technology
    if any(pattern in s_lower for pattern in [
        "b.tech", "btech", "b. tech", "bachelor of technology"
    ]):
        return "B.Tech"

    # 5. MBA / Master of Business Administration
    if "mba" in s_lower or "m.b.a" in s_lower or "master of business administration" in s_lower:
        return "MBA"

    # 6. M.E. / Master of Engineering
    if "master of engineering" in s_lower or "m.e" in s_lower or s_lower == "me" or re.search(r"\bm\.?e\.?\b", s_lower):
        if not ("mech" in s_lower or "media" in s_lower):
            return "M.E."

    # 7. B.E. / Bachelor of Engineering
    if "bachelor of engineering" in s_lower or "b.e" in s_lower or s_lower == "be" or re.search(r"\bb\.?e\.?\b", s_lower):
        return "B.E."

    # 8. MCA / Master of Computer Applications / Master of Computer Science
    if any(pattern in s_lower for pattern in [
        "mca", "m.c.a", "master of computer application", "masters in computer application"
    ]):
        return "MCA"
    if "msc cs" in s_lower or "master of computer science" in s_lower:
        return "MCA"

    # 9. BCA / Bachelor of Computer Applications
    if any(pattern in s_lower for pattern in [
        "bca", "b.c.a", "bachelor of computer application"
    ]):
        return "BCA"

    # 10. M.Sc. / Master of Science
    if any(pattern in s_lower for pattern in [
        "m.sc", "msc", "m. sc", "m sc", "master of science", "masters of science", "master in science"
    ]):
        return "M.Sc."

    # 11. B.Sc. / Bachelor of Science
    if any(pattern in s_lower for pattern in [
        "b.sc", "bsc", "b. sc", "b sc", "bachelor of science", "bachelor in science"
    ]):
        return "B.Sc."

    # 12. M.Phil. / Master of Philosophy
    if "m.phil" in s_lower or "mphil" in s_lower or "master of philosophy" in s_lower:
        return "M.Phil."

    # 13. M.S. / Master of Science (abbreviated MS)
    if re.search(r"\bm\.?s\.?\b", s_lower):
        return "M.S."

    # 14. M.A. / Master of Arts / MSW
    if any(pattern in s_lower for pattern in [
        "m.a", "master of arts", "master in arts", "master of social work", "msw"
    ]):
        return "M.A."

    # 15. B.A. / Bachelor of Arts
    if any(pattern in s_lower for pattern in [
        "b.a", "ba(h)", "bachelor of arts"
    ]):
        return "B.A."

    # 16. B.Ed / Bachelor of Education
    if "b.ed" in s_lower or "bachelor of education" in s_lower:
        return "B.Ed"

    # 17. Diploma
    if "diploma" in s_lower:
        return "Diploma"

    # 18. Higher Secondary (12th)
    if any(pattern in s_lower for pattern in [
        "12th", "10+2", "hsc", "h.s.c", "higher secondary", "senior secondary",
        "intermediate", "pre degree", "w.b.c.h.s.e", "a levels"
    ]):
        return "Higher Secondary (12th)"

    # 19. Secondary (10th)
    if any(pattern in s_lower for pattern in [
        "10th", "ssc", "s.s.c", "secondary", "high school", "madhyamik",
        "matric", "metric", "sslc", "w.b.b.s.e"
    ]):
        return "Secondary (10th)"

    return "Other"


def get_degree_rank(canonical_degree: str) -> int:
    """Return academic hierarchy rank for a canonical degree."""
    return DEGREE_HIERARCHY.get(canonical_degree, 10)


def get_highest_canonical_degree(education_list: List[Dict[str, Any]]) -> str:
    """
    Evaluate all education entries for a candidate and return the highest
    canonical degree according to academic rank hierarchy.
    """
    if not education_list or not isinstance(education_list, list):
        return "Other"

    highest_degree = "Other"
    highest_rank = 0

    for item in education_list:
        if not isinstance(item, dict):
            continue
        raw_degree = item.get("degree", "")
        norm_degree = normalize_degree(raw_degree)
        rank = get_degree_rank(norm_degree)

        if rank > highest_rank:
            highest_rank = rank
            highest_degree = norm_degree

    return highest_degree


def normalize_candidate_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich candidate JSON data with normalized_degree in education
    and normalized_highest_degree at top level without modifying raw degree strings.
    """
    if not isinstance(data, dict):
        return data

    education = data.get("education", [])
    if isinstance(education, list):
        for item in education:
            if isinstance(item, dict) and "degree" in item:
                item["normalized_degree"] = normalize_degree(item["degree"])

    data["normalized_highest_degree"] = get_highest_canonical_degree(education)
    return data
