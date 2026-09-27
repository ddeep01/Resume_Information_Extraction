from typing import List, Dict, Any

def calculate_education_score(education_list: List[Dict[str, Any]]) -> float:
    if not education_list:
        return 0.33

    total_weight = 0.0
    weighted_score = 0.0

    for edu in education_list:
        qtype = (edu.get("qualification_type") or "").upper()
        inst_score = float(edu.get("institution_score") or 0.33)

        if "PHD" in qtype or "PDF" in qtype:
            w = 0.50
        elif "PG" in qtype or "MASTER" in qtype or "M.TECH" in qtype:
            w = 0.30
        elif "UG" in qtype or "BACHELOR" in qtype or "B.TECH" in qtype:
            w = 0.20
        else:
            w = 0.10

        weighted_score += inst_score * w
        total_weight += w

    if total_weight > 0:
        return round(weighted_score / total_weight, 4)
    return 0.33

def calculate_publication_score(window_publications: List[Dict[str, Any]], target_min_pubs: int = 5) -> float:
    if not window_publications:
        return 0.0

    count = len(window_publications)
    # 1. Quantity component (max out at 2x target_min_pubs)
    max_target = max(target_min_pubs * 2, 8)
    quantity_score = min(count / max_target, 1.0)

    # 2. Quality component (venue tiers)
    venue_scores = [float(pub.get("venue_score") or 0.33) for pub in window_publications]
    avg_quality = sum(venue_scores) / len(venue_scores) if venue_scores else 0.33

    # Weighted combination: 40% quantity, 60% quality
    combined = (quantity_score * 0.4) + (avg_quality * 0.6)
    return round(combined, 4)

def calculate_academic_experience_score(academic_exp_list: List[Dict[str, Any]]) -> float:
    if not academic_exp_list:
        return 0.0

    total_years = sum(float(item.get("duration_years") or 0.0) for item in academic_exp_list)

    # Duration score capped at 10 years
    duration_score = min(total_years / 10.0, 1.0)

    # Institution tier score
    inst_scores = [float(item.get("institution_score") or 0.33) for item in academic_exp_list]
    avg_inst = sum(inst_scores) / len(inst_scores) if inst_scores else 0.33

    combined = (duration_score * 0.5) + (avg_inst * 0.5)
    return round(combined, 4)

def calculate_industry_experience_score(industry_exp_list: List[Dict[str, Any]]) -> float:
    if not industry_exp_list:
        return 0.0

    total_years = sum(float(item.get("duration_years") or 0.0) for item in industry_exp_list)

    # Duration score capped at 8 years
    return round(min(total_years / 8.0, 1.0), 4)

def calculate_final_score(
    education_score: float,
    publication_score: float,
    academic_exp_score: float,
    industry_exp_score: float,
    weights: Dict[str, float]
) -> float:
    w_edu = weights.get("education", 0.35)
    w_pub = weights.get("publication", 0.30)
    w_acad = weights.get("academic_experience", 0.20)
    w_ind = weights.get("industry_experience", 0.15)

    final_normalized = (
        (education_score * w_edu) +
        (publication_score * w_pub) +
        (academic_exp_score * w_acad) +
        (industry_exp_score * w_ind)
    )

    return round(final_normalized * 100.0, 2)
