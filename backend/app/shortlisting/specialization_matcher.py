import re
from typing import List, Dict, Any

ALIASES = {
    "computer science": ["cs", "cse", "computer science and engineering", "computer application", "computer applications", "information technology", "it", "ai", "artificial intelligence", "machine learning", "data science"],
    "artificial intelligence": ["ai", "machine learning", "ml", "computer science", "data science", "deep learning"],
    "information technology": ["it", "computer science", "cse", "information systems"],
}

def matches_specialization(required_spec: str, candidate_streams: List[str]) -> tuple[bool, str]:
    if not required_spec or not required_spec.strip() or required_spec.strip().lower() == "any":
        return True, "No specialization requirement"

    req = required_spec.strip().lower()
    req_tokens = set(re.findall(r"\w+", req))

    # Check against all streams extracted from candidate's education
    for stream in candidate_streams:
        if not stream or not isinstance(stream, str):
            continue
        c_str = stream.strip().lower()

        # 1. Exact or Substring match
        if req in c_str or c_str in req:
            return True, f"Specialization matched: '{stream}' matches required '{required_spec}'"

        # 2. Token overlap match (e.g. "Computer Science" vs "Computer Science and Engineering")
        c_tokens = set(re.findall(r"\w+", c_str))
        if req_tokens.issubset(c_tokens) or c_tokens.issubset(req_tokens):
            return True, f"Specialization token match: '{stream}' matches '{required_spec}'"

        # 3. Alias dictionary check
        for key, aliases in ALIASES.items():
            if key in req or req in key:
                if any(alias in c_str for alias in aliases):
                    return True, f"Specialization alias match: '{stream}' matches required category '{required_spec}'"

    return False, f"Required specialization '{required_spec}' not matched in candidate streams: {', '.join(candidate_streams) if candidate_streams else 'None'}"
