from typing import List, Dict, Any

def rank_and_shortlist_candidates(candidates: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    """
    Ranks eligible candidates by final_score descending, selects Top-N,
    and updates shortlisting fields for all candidates.
    """
    eligible_candidates = []
    ineligible_candidates = []

    for cand in candidates:
        shortlisting = cand.get("shortlisting", {})
        if shortlisting.get("eligible", False):
            eligible_candidates.append(cand)
        else:
            cand["shortlisting"]["shortlisted"] = False
            cand["shortlisting"]["rank"] = None
            ineligible_candidates.append(cand)

    # Sort eligible candidates by final_score descending
    eligible_candidates.sort(
        key=lambda c: c.get("shortlisting", {}).get("final_score", 0.0),
        reverse=True
    )

    # Assign rank and shortlist Top N
    for index, cand in enumerate(eligible_candidates, start=1):
        cand["shortlisting"]["rank"] = index
        if index <= top_n:
            cand["shortlisting"]["shortlisted"] = True
            cand["shortlisting"]["reasons"].insert(0, f"SHORTLISTED: Ranked #{index} among eligible candidates (Score: {cand['shortlisting']['final_score']}/100)")
        else:
            cand["shortlisting"]["shortlisted"] = False
            cand["shortlisting"]["reasons"].insert(0, f"NOT SHORTLISTED: Ranked #{index} (Top {top_n} cutoff, Score: {cand['shortlisting']['final_score']}/100)")

    return eligible_candidates + ineligible_candidates
