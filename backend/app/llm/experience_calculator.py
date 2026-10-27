import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ExperienceCalculator")

MONTHS_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

WORD_NUMBERS = {
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0, "fifteen": 15.0,
    "twenty": 20.0, "decade": 10.0, "a decade": 10.0
}

CURRENT_MARKERS = {
    "present", "current", "till date", "to date", "ongoing", "now",
    "presently", "currently", "continuing", "till now", "active", "presently working"
}

EXPLICIT_EXP_PATTERNS = [
    # A decade of experience
    r"\b(?:a\s+)?decade(?:\s+of)?(?:\s+(?:professional|industry|relevant|software|hands-on|work|it|technical|academic|teaching))?\s*experience\b",
    # Over / More than / approx X years of experience
    r"\b(?:over|more than|greater than|at least|above|approx(?:imately)?|nearly|around)\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:professional|industry|relevant|total|work|it|software|hands-on|technical|academic|teaching))?\s*experience\b",
    # X+ years of experience
    r"\b(\d+(?:\.\d+)?)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?(?:\s+(?:professional|industry|relevant|total|work|it|software|hands-on|technical|academic|teaching))?\s*experience\b",
    # Word numbers + years of experience (e.g. six years of experience)
    r"\b(" + "|".join(WORD_NUMBERS.keys()) + r")\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:professional|industry|relevant|total|work|it|software|hands-on|technical|academic|teaching))?\s*experience\b",
    # Experience of X years
    r"\bexperience\s+of\s+(?:over\s+|more than\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b",
    # X years in software development / IT / etc.
    r"\b(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:in|of)\s+(?:software|web|full[- ]stack|machine learning|data science|it|cloud|academic|teaching|research|engineering)\b"
]


def parse_date_to_decimal(date_val: Any, is_end_date: bool = False, current_year: Optional[int] = None, current_month: Optional[int] = None) -> Optional[float]:
    """
    Parse a date string or number into a decimal year representation (e.g., June 2020 -> 2020.5).
    Handles:
    - Month Name YYYY (January 2018, Jan 2018)
    - MM/YYYY, MM-YYYY, MM.YYYY (01/2018, 12/2020)
    - YYYY-MM (2018-01, 2020-12)
    - YYYY (2018, 2020)
    - Present, Current, Till Date, Ongoing, Now
    """
    if date_val is None:
        return None

    if isinstance(date_val, (int, float)):
        val = float(date_val)
        if 1950 <= val <= 2050:
            return val + (1.0 if is_end_date else 0.0)
        return None

    s = str(date_val).strip()
    if not s or s.lower() in ("null", "none", "n/a", "na", "undefined", "-"):
        return None

    s_lower = s.lower().strip()

    # Check for Present / Current markers
    if any(m in s_lower for m in CURRENT_MARKERS):
        now = datetime.now()
        c_year = current_year if current_year is not None else now.year
        c_month = current_month if current_month is not None else now.month
        return c_year + (c_month / 12.0)

    # Check MM/YYYY or MM-YYYY or MM.YYYY
    m = re.search(r"\b(0?[1-9]|1[0-2])[\/\.-]((?:19|20)\d{2})\b", s)
    if m:
        month = int(m.group(1))
        year = int(m.group(2))
        return year + ((month - 1) / 12.0) if not is_end_date else year + (month / 12.0)

    # Check YYYY-MM or YYYY/MM
    m = re.search(r"\b((?:19|20)\d{2})[\/\.-](0?[1-9]|1[0-2])\b", s)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        return year + ((month - 1) / 12.0) if not is_end_date else year + (month / 12.0)

    # Check Month Name YYYY (e.g. January 2018, Jan 2018, Jan. 2018)
    for m_name, m_val in MONTHS_MAP.items():
        m = re.search(r"\b" + m_name + r"\.?\s+((?:19|20)\d{2})\b", s_lower)
        if m:
            year = int(m.group(1))
            return year + ((m_val - 1) / 12.0) if not is_end_date else year + (m_val / 12.0)

    # Check YYYY only
    m = re.search(r"\b((?:19|20)\d{2})\b", s)
    if m:
        year = int(m.group(1))
        # When only year is available: start defaults to beginning of year, end defaults to end of year
        return float(year) if not is_end_date else float(year) + 1.0

    return None


def calculate_interval_duration(start_str: Any, end_str: Any, current_year: Optional[int] = None, current_month: Optional[int] = None) -> float:
    """
    Calculate the duration between start and end date strings in years.
    Returns 0.0 if dates cannot be determined.
    """
    s_dec = parse_date_to_decimal(start_str, is_end_date=False, current_year=current_year, current_month=current_month)
    e_dec = parse_date_to_decimal(end_str, is_end_date=True, current_year=current_year, current_month=current_month)

    if s_dec is None or e_dec is None:
        return 0.0

    diff = e_dec - s_dec
    return max(0.0, round(diff, 2))


def merge_intervals(intervals: List[Tuple[float, float]]) -> float:
    """
    Interval Union Algorithm:
    Merges overlapping or contiguous employment intervals and calculates total non-overlapping duration.
    - Overlapping periods are counted only once.
    - Career gaps between intervals are not counted.
    """
    valid = [(s, e) for s, e in intervals if s is not None and e is not None and e >= s]
    if not valid:
        return 0.0

    valid.sort(key=lambda x: x[0])
    merged = [valid[0]]

    for cur_s, cur_e in valid[1:]:
        prev_s, prev_e = merged[-1]
        if cur_s <= prev_e:
            # Overlap detected: extend the current interval
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append((cur_s, cur_e))

    total = sum(e - s for s, e in merged)
    return max(0.0, round(total, 2))


def extract_explicit_experience_from_text(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Scans entire resume text for explicitly stated total experience phrases.
    Returns: (years: Optional[float], matched_text: Optional[str])
    """
    if not text:
        return None, None

    for pattern in EXPLICIT_EXP_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matched_str = match.group(0).strip()
            if "decade" in matched_str.lower():
                return 10.0, matched_str
            for g in match.groups():
                if g:
                    gl = g.lower()
                    if gl in WORD_NUMBERS:
                        return WORD_NUMBERS[gl], matched_str
                    try:
                        return float(gl), matched_str
                    except ValueError:
                        pass
    return None, None


def is_internship_entry(item: Dict[str, Any]) -> bool:
    """Detect if an experience record represents an internship or trainee role."""
    texts = [
        str(item.get("role") or ""),
        str(item.get("job_title") or ""),
        str(item.get("description") or ""),
        str(item.get("employment_type") or "")
    ]
    combined = " ".join(texts).lower()
    intern_keywords = ["intern", "internship", "trainee", "summer intern", "graduate intern", "apprentice"]
    return any(k in combined for k in intern_keywords)


def is_non_professional_activity(item: Dict[str, Any]) -> bool:
    """Detect if an experience record is actually an academic project, course, or certification."""
    return is_unrelated_experience_item(item)


def is_unrelated_experience_item(item: Dict[str, Any]) -> bool:
    """
    Detect if an extracted record is actually an unrelated activity:
    - university accreditation / NAAC information
    - research topics / interests
    - publications / papers / patents
    - academic projects / capstone / coursework
    - degree study periods
    - certifications / trainings / workshops
    """
    texts = [
        str(item.get("role") or ""),
        str(item.get("job_title") or ""),
        str(item.get("designation") or ""),
        str(item.get("description") or ""),
        str(item.get("organization") or ""),
        str(item.get("company_name") or ""),
        str(item.get("institution") or "")
    ]
    combined = " ".join(texts).lower()

    # 1. NAAC & Accreditation
    if any(k in combined for k in ("naac", "accreditation", "nba 2.0", "naac cycle", "abet")):
        return True

    # 2. Research topics / areas of interest
    if any(k in combined for k in ("areas of research", "area of interest", "research interests", "research topics", "area of specialization")):
        return True

    # 3. Publications & Patents
    if any(k in combined for k in ("journal articles", "conference paper", "publications profile", "published in", "patent title", "paper title")):
        return True

    # 4. Academic Projects & Theses
    if any(k in combined for k in ("capstone project", "coursework", "college project", "b.tech project", "m.tech thesis", "academic project", "phd thesis", "dissertation:")):
        return True

    # 5. Certifications & Workshop attendance
    if any(k in combined for k in ("nptel", "coursera", "udemy", "online certificate", "participation in workshop", "participation in conference")):
        return True

    return False


def clean_and_calculate_experience_list(
    exp_list: Any,
    raw_total_exp: Optional[float] = None,
    full_resume_text: str = "",
    current_year: Optional[int] = None,
    current_month: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Cleans and standardizes the experience list according to the required schema:
    {
      "experience_type": "academic" | "professional",
      "institution": str,
      "role": str,
      "start_date": str or None,
      "end_date": str or None,
      "duration_years": float,
      "description": str or None
    }
    Calculates candidate-level total_experience without double-counting overlapping periods.
    """
    if not isinstance(exp_list, list):
        if isinstance(exp_list, dict):
            # Convert dictionary of academic/professional/industry to list
            exp_list = (exp_list.get("academic") or []) + (exp_list.get("professional") or exp_list.get("industry") or [])
        else:
            exp_list = []

    now = datetime.now()
    c_year = current_year if current_year is not None else now.year
    c_month = current_month if current_month is not None else now.month

    cleaned_records = []
    intervals = []
    dur_without_dates = 0.0

    for raw_item in exp_list:
        if not isinstance(raw_item, dict):
            continue

        # Check for template placeholder text
        inst = str(raw_item.get("institution") or raw_item.get("company_name") or raw_item.get("organization") or raw_item.get("company") or "").strip()
        role = str(raw_item.get("role") or raw_item.get("job_title") or raw_item.get("designation") or "").strip()

        if not inst and not role:
            continue
        if "university / institute / company" in inst.lower() or "designation / role" in role.lower():
            continue

        # Check if it's an unrelated activity (NAAC, degree, publication, project, cert)
        if is_unrelated_experience_item(raw_item):
            continue

        # Determine experience_type: exactly "academic" or "professional"
        # User requirement:
        # - "academic": Research fellow/scholar, JRF/SRF, Postdoc/postdoctoral fellow, project fellow/associate, graduate/teaching assistant.
        # - "professional": Actual teaching experience (faculty, lecturer, professor, reader, instructor) and industry/corporate experience.
        exp_type_raw = str(raw_item.get("experience_type") or "").lower().strip()
        role_lower = role.lower()
        role_inst_combined = f"{role} {inst}".lower()

        # Pure academic research fellowships / scholars / postdocs
        fellowship_keywords = (
            "research fellow", "research scholar", "jrf", "srf", "junior research fellow",
            "senior research fellow", "postdoc", "post doctoral", "post-doctoral",
            "postdoctoral fellow", "postdoctoral researcher", "postdoctoral scholar",
            "project fellow", "project associate", "teaching assistant", "graduate assistant"
        )
        # Professional teaching faculty roles
        teaching_faculty_keywords = (
            "professor", "lecturer", "faculty", "reader", "instructor", "dean", "director", "principal", "hod", "teacher"
        )

        if any(k in role_lower for k in teaching_faculty_keywords):
            final_exp_type = "professional"
        elif any(k in role_inst_combined for k in fellowship_keywords):
            final_exp_type = "academic"
        elif "acad" in exp_type_raw and not any(k in role_lower for k in teaching_faculty_keywords):
            final_exp_type = "academic"
        else:
            final_exp_type = "professional"

        # Dates
        start_date = raw_item.get("start_date")
        end_date = raw_item.get("end_date")

        # Parse duration
        dur_val = raw_item.get("duration_years")
        dur_float = 0.0
        if dur_val is not None:
            try:
                dur_float = float(dur_val)
            except (ValueError, TypeError):
                dur_float = 0.0

        # Calculate duration from dates if not given or 0
        calc_dur = calculate_interval_duration(start_date, end_date, current_year=c_year, current_month=c_month)
        if calc_dur > 0.0 and dur_float <= 0.0:
            dur_float = calc_dur

        desc = raw_item.get("description")
        if desc and str(desc).lower() in ("null", "none", ""):
            desc = None

        record = {
            "experience_type": final_exp_type,
            "institution": inst or None,
            "role": role or None,
            "start_date": str(start_date).strip() if start_date and str(start_date).lower() not in ("null", "none") else None,
            "end_date": str(end_date).strip() if end_date and str(end_date).lower() not in ("null", "none") else None,
            "duration_years": round(max(0.0, dur_float), 2),
            "description": str(desc).strip() if desc else None
        }

        # Deduplication check for identical institution & role
        inst_lower = (record["institution"] or "").strip().lower()
        role_lower = (record["role"] or "").strip().lower()
        key = f"{inst_lower}:{role_lower}"

        merged_with_existing = False
        if key != ":":
            for existing in cleaned_records:
                ex_inst = (existing.get("institution") or "").strip().lower()
                ex_role = (existing.get("role") or "").strip().lower()
                if f"{ex_inst}:{ex_role}" == key:
                    ex_start = existing.get("start_date")
                    ex_end = existing.get("end_date")
                    rec_start = record.get("start_date")
                    rec_end = record.get("end_date")
                    # If dates match, or either is missing, merge into existing record
                    if (not ex_start and not ex_end) or (not rec_start and not rec_end) or (ex_start == rec_start and ex_end == rec_end) or (ex_start == rec_start) or (ex_end == rec_end):
                        for k, v in record.items():
                            if v is not None and not existing.get(k):
                                existing[k] = v
                        if (record.get("duration_years") or 0.0) > (existing.get("duration_years") or 0.0):
                            existing["duration_years"] = record["duration_years"]
                        merged_with_existing = True
                        break

        if not merged_with_existing:
            cleaned_records.append(record)

            # Collect intervals for total_experience calculation
            s_dec = parse_date_to_decimal(record["start_date"], is_end_date=False, current_year=c_year, current_month=c_month)
            e_dec = parse_date_to_decimal(record["end_date"], is_end_date=True, current_year=c_year, current_month=c_month)

            if s_dec is not None and e_dec is not None and e_dec >= s_dec:
                intervals.append((s_dec, e_dec))
            elif record["duration_years"] > 0.0:
                dur_without_dates += record["duration_years"]

    # Calculate candidate-level total_experience
    merged_total = merge_intervals(intervals) + dur_without_dates

    # Use raw_total_exp if provided by LLM (do not return 0 if intervals or explicit states otherwise)
    final_total_exp = 0.0
    if raw_total_exp is not None:
        try:
            parsed_total = float(raw_total_exp)
            final_total_exp = max(parsed_total, merged_total)
        except (ValueError, TypeError):
            final_total_exp = merged_total
    else:
        final_total_exp = merged_total

    # Fallback to explicit regex scan only if full_resume_text given and total is still 0
    if final_total_exp == 0.0 and full_resume_text:
        found_years, _ = extract_explicit_experience_from_text(full_resume_text)
        if found_years is not None:
            final_total_exp = found_years

    final_total_exp = round(max(0.0, final_total_exp), 2)
    return cleaned_records, final_total_exp


def clean_and_calculate_experience_dict(
    exp_data: Any,
    raw_total_exp: Optional[float] = None,
    full_resume_text: str = "",
    current_year: Optional[int] = None,
    current_month: Optional[int] = None
) -> Tuple[Dict[str, List[Dict[str, Any]]], float]:
    """
    Cleans and standardizes experience into a dictionary with two sections:
    {
      "academic": [...],
      "professional": [...]
    }
    where:
    - "academic": Genuine research fellowships, research scholars, JRF, SRF, Postdoctoral Fellows / Postdocs.
    - "professional": Actual teaching experience (faculty, lecturer, professor) and industry employment.
    Also provides "industry" as backward-compatible alias to "professional".
    Calculates candidate-level total_experience without double-counting overlapping periods.
    """
    raw_items = []
    if isinstance(exp_data, dict):
        for it in (exp_data.get("academic") or []):
            if isinstance(it, dict):
                it_copy = dict(it)
                if not it_copy.get("experience_type"):
                    it_copy["experience_type"] = "academic"
                raw_items.append(it_copy)
        for it in (exp_data.get("professional") or exp_data.get("industry") or []):
            if isinstance(it, dict):
                it_copy = dict(it)
                if not it_copy.get("experience_type"):
                    it_copy["experience_type"] = "professional"
                raw_items.append(it_copy)
    elif isinstance(exp_data, list):
        raw_items = exp_data
    else:
        raw_items = []

    cleaned_records, total_exp = clean_and_calculate_experience_list(
        raw_items,
        raw_total_exp=raw_total_exp,
        full_resume_text=full_resume_text,
        current_year=current_year,
        current_month=current_month
    )

    acad_list = [r for r in cleaned_records if r.get("experience_type") == "academic"]
    prof_list = [r for r in cleaned_records if r.get("experience_type") == "professional"]

    exp_dict = {
        "academic": acad_list,
        "professional": prof_list,
        "industry": prof_list  # backward-compatible alias
    }
    return exp_dict, total_exp


def normalize_experience_item(item: Dict[str, Any], exp_type: str = "industry", current_year: Optional[int] = None, current_month: Optional[int] = None) -> Dict[str, Any]:
    """
    Normalize fields of a single experience record for backward and forward compatibility:
    - job_title <-> role
    - company_name <-> organization / institution
    - start_date, end_date, duration_years
    - is_current, is_internship, employment_type
    """
    normalized = dict(item)

    # 1. Designation / Role normalization
    role = item.get("role") or item.get("job_title") or item.get("designation") or "Professional Role"
    normalized["role"] = role
    normalized["job_title"] = role

    # 2. Employer / Institution normalization
    org = item.get("organization") or item.get("company_name") or item.get("company") or item.get("institution") or "Organization"
    normalized["organization"] = org
    normalized["company_name"] = org
    if exp_type == "academic":
        normalized["institution"] = org

    # 3. Dates & duration
    start_date = item.get("start_date")
    end_date = item.get("end_date")

    # If start_date/end_date not present, check if duration string contains dates e.g. "2018 - 2022"
    dur_str = str(item.get("duration") or item.get("period") or "")
    if (not start_date or not end_date) and dur_str:
        parts = re.split(r"\s*(?:-|–|to|until)\s*", dur_str)
        if len(parts) >= 2:
            if not start_date:
                start_date = parts[0].strip()
            if not end_date:
                end_date = parts[1].strip()

    normalized["start_date"] = start_date
    normalized["end_date"] = end_date

    # Check is_current
    end_str_lower = str(end_date or "").lower()
    is_curr = item.get("is_current", False) or any(m in end_str_lower for m in CURRENT_MARKERS)
    normalized["is_current"] = bool(is_curr)

    # Calculate duration if not provided or 0.0
    existing_dur = float(item.get("duration_years") or 0.0)
    calc_dur = calculate_interval_duration(start_date, end_date, current_year=current_year, current_month=current_month)
    
    if calc_dur > 0.0:
        normalized["duration_years"] = calc_dur
    elif existing_dur > 0.0:
        normalized["duration_years"] = existing_dur
    else:
        normalized["duration_years"] = 0.0

    # 4. Check Internship
    normalized["is_internship"] = is_internship_entry(item)
    emp_type = item.get("employment_type")
    if not emp_type:
        normalized["employment_type"] = "internship" if normalized["is_internship"] else "full_time"
    else:
        normalized["employment_type"] = emp_type

    normalized["description"] = item.get("description")
    normalized["experience_type"] = exp_type

    return normalized


def calculate_and_enrich_experience(
    experience_data: Dict[str, Any],
    full_resume_text: str = "",
    current_year: Optional[int] = None,
    current_month: Optional[int] = None
) -> Dict[str, Any]:
    """
    Master pipeline experience analyzer & calculator:
    1. Normalizes all academic and industry employment entries.
    2. Calculates individual durations from dates.
    3. Merges non-overlapping employment intervals to calculate true total experience (excluding gaps and overlaps).
    4. Extracts any explicitly stated total experience from full resume text.
    5. Sets calculation basis and flags discrepancies if explicit experience disagrees with employment history.
    6. Distinguishes zero experience from unavailable dates.
    """
    if not isinstance(experience_data, dict):
        experience_data = {}

    now = datetime.now()
    c_year = current_year if current_year is not None else now.year
    c_month = current_month if current_month is not None else now.month

    # 1. Normalize Academic and Industry items
    raw_acad = experience_data.get("academic", [])
    raw_ind = experience_data.get("industry", [])

    if not isinstance(raw_acad, list):
        raw_acad = []
    if not isinstance(raw_ind, list):
        raw_ind = []

    norm_acad = [normalize_experience_item(a, exp_type="academic", current_year=c_year, current_month=c_month) for a in raw_acad if isinstance(a, dict)]
    norm_ind = [normalize_experience_item(i, exp_type="industry", current_year=c_year, current_month=c_month) for i in raw_ind if isinstance(i, dict)]

    # Filter out student coursework/capstone project non-work entries if accidentally classified
    norm_acad = [a for a in norm_acad if not is_non_professional_activity(a)]
    norm_ind = [i for i in norm_ind if not is_non_professional_activity(i)]

    # 2. Gather non-overlapping intervals for full-time professional experience
    intervals = []
    has_dated_records = False
    has_undated_records = False

    for item in norm_acad + norm_ind:
        # Check if internship
        if item.get("is_internship"):
            continue

        s_dec = parse_date_to_decimal(item.get("start_date"), is_end_date=False, current_year=c_year, current_month=c_month)
        e_dec = parse_date_to_decimal(item.get("end_date"), is_end_date=True, current_year=c_year, current_month=c_month)

        if s_dec is not None and e_dec is not None and e_dec >= s_dec:
            intervals.append((s_dec, e_dec))
            has_dated_records = True
        elif item.get("duration_years", 0.0) > 0.0:
            # Single duration without dates: approximate interval
            d = item["duration_years"]
            intervals.append((c_year - d, c_year))
            has_dated_records = True
        else:
            has_undated_records = True

    calculated_total_years = merge_intervals(intervals)

    # If interval union is 0 (e.g. narrative or natural descriptive dates), preserve the LLM's inferred total
    llm_calc_years = experience_data.get("calculated_total_years")
    if calculated_total_years == 0.0 and llm_calc_years is not None:
        try:
            val = float(llm_calc_years)
            if val > 0.0:
                calculated_total_years = val
                has_dated_records = True
        except (ValueError, TypeError):
            pass

    # 3. Check for explicitly mentioned total experience in text or input
    explicit_years = experience_data.get("explicitly_mentioned_years")
    explicit_text = experience_data.get("explicit_experience_text")

    if explicit_years is None and full_resume_text:
        found_years, found_text = extract_explicit_experience_from_text(full_resume_text)
        if found_years is not None:
            explicit_years = found_years
            explicit_text = found_text

    # 4. Determine calculation basis & status
    calculation_basis = "not_specified"
    experience_status = "unavailable"
    discrepancy_note = None

    has_records = len(norm_acad) + len(norm_ind) > 0

    if explicit_years is not None and calculated_total_years > 0.0:
        # Both available: check for discrepancy
        diff = abs(explicit_years - calculated_total_years)
        # Discrepancy threshold: more than 2 years difference or > 50% relative divergence
        max_val = max(explicit_years, calculated_total_years)
        if diff >= 2.0 and (max_val > 0 and (diff / max_val) > 0.4):
            experience_status = "discrepancy_detected"
            discrepancy_note = (
                f"Discrepancy detected: Candidate profile explicitly mentions {explicit_years} years of experience "
                f"('{explicit_text}'), but documented employment history calculates to {calculated_total_years} years."
            )
            calculation_basis = "discrepancy"
        else:
            experience_status = "available"
            calculation_basis = "calculated_from_history" if has_dated_records else "explicitly_stated"

    elif calculated_total_years > 0.0:
        experience_status = "available"
        calculation_basis = "calculated_from_history"

    elif explicit_years is not None and explicit_years > 0.0:
        experience_status = "available"
        calculation_basis = "explicitly_stated"
        calculated_total_years = explicit_years

    elif has_records and has_undated_records and not has_dated_records:
        # Candidate has employment records but no dates or durations provided
        experience_status = "unavailable"
        calculation_basis = "not_specified"
        calculated_total_years = 0.0

    elif not has_records and (explicit_years is None or explicit_years == 0.0):
        # Candidate has no employment records and no experience mentioned
        experience_status = "zero_experience"
        calculation_basis = "not_specified"
        calculated_total_years = 0.0

    else:
        experience_status = "unavailable"
        calculation_basis = "not_specified"
        calculated_total_years = 0.0

    # Respect valid LLM-determined status or basis if calculator remained unspecific
    llm_basis = experience_data.get("calculation_basis")
    if calculation_basis == "not_specified" and llm_basis in ("explicitly_stated", "calculated_from_history", "discrepancy"):
        calculation_basis = llm_basis

    llm_status = experience_data.get("experience_status")
    if experience_status == "unavailable" and llm_status in ("available", "zero_experience", "discrepancy_detected"):
        experience_status = llm_status

    # Build final clean enriched experience dict
    enriched = {
        "explicitly_mentioned_years": explicit_years,
        "explicit_experience_text": explicit_text,
        "calculated_total_years": calculated_total_years,
        "calculation_basis": calculation_basis,
        "experience_status": experience_status,
        "discrepancy_note": discrepancy_note,
        "academic": norm_acad,
        "industry": norm_ind
    }

    return enriched
