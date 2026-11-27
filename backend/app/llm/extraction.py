import re
import json
import time
import hashlib
import logging
import requests
from typing import Dict, Any, Optional, List

from backend.app.config import settings
from backend.app.llm.base import LLMProvider
from backend.app.llm.ollama_provider import OllamaProvider
from backend.app.llm.remote_provider import OpenAIProvider
from backend.app.llm.token_counter import TokenCounter
from backend.app.llm.splitter import RecursiveTextSplitter, Chunk
from backend.app.llm.json_validator import JSONValidator
from backend.app.llm.merger import HierarchicalMerger
from backend.app.llm.chunk_cache import ChunkCache
from backend.app.llm.retry_handler import RetryHandler
from backend.app.llm.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
    LEAF_EXTRACTION_USER_PROMPT_TEMPLATE
)

logger = logging.getLogger("LLMExtractor")

def get_llm_provider() -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "ollama":
        try:
            res = requests.get(f"{settings.LLM_BASE_URL.rstrip('/')}/api/tags", timeout=5)
            if res.status_code == 200:
                return OllamaProvider()
            else:
                raise RuntimeError(f"Ollama server returned status code {res.status_code} at {settings.LLM_BASE_URL}")
        except Exception as e:
            raise RuntimeError(
                f"LLM Connection Error: Ollama is unreachable at {settings.LLM_BASE_URL} ({e}). "
                f"Please start Ollama service using 'ollama run {settings.LLM_MODEL}' to process resumes."
            )
    elif provider_name == "openai":
        return OpenAIProvider()
    else:
        raise RuntimeError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

from backend.app.schemas.candidate import EducationItem, PersonalInformation, PublicationItem, sanitize_string_value, infer_qualification_type

def extract_candidate_name_from_text(text: str) -> Optional[str]:
    """Extract candidate full name from the top header lines of a resume text."""
    if not text:
        return None
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:25]:
        if not line or re.fullmatch(r'\d+', line):
            continue
        if any(k in line.lower() for k in (
            'curriculum', 'curiculam', 'vitae', 'resume', 'biodata', 'profile', 'page ',
            'http', '@', '+91', 'phone', 'email', 'objective', 'summary', 'career',
            'qualification', 'certificate', 'academic', 'experience', 'education',
            'linkedin', 'github', 'scholar', 'publications', 'declaration'
        )):
            continue
        cleaned = re.sub(r'^[^\w]+', '', line).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 5 and all(re.match(r'^[A-Za-z\.\'\-]+$', w) for w in words):
            return cleaned.title() if cleaned.isupper() else cleaned
    return None

def extract_education_from_section(text: str) -> List[Dict[str, Any]]:
    """Robust fallback extractor for academic qualifications from resume text."""
    if not text:
        return []
    m = re.search(
        r'(?:^|\n)\s*(?:Education|Academic Qualifications|Educational Qualifications|Academic Background|Qualifications|Educational Background)\b(.*?)(?:\n\s*(?:Employment|Experience|Work Experience|Professional Experience|Research Experience|Technical Skills|Skills|Projects|Publications|Awards|Achievements)|\Z)',
        text, re.I | re.S
    )
    if not m:
        return []

    edu_text = m.group(1)
    lines = [l.strip() for l in edu_text.split('\n') if l.strip()]

    deg_specs = [
        ('PhD', r'\b(?:Doctor\s+of\s+Philosophy|\(?Ph\.?\s*D\.?\)?|Doctorate|D\.?\s*Phil)\b'),
        ('Post Doctoral', r'\b(?:Post[- ]?Doctoral|Post[- ]?Doc(?:toral)?|PDF)\b'),
        ('PG', r'\b(?:Master\s+of\s+Technology|Master\s+of\s+Science|Master\s+of\s+Engineering|Master\s+of\s+Commerce|Master\s+of\s+Arts|MCA|MBA|M\.?\s*Phil|\(?M\.?\s*Tech\.?\)?|\(?M\.?\s*Sc\.?\)?|\(?M\.?\s*E\.?\)?|\(?M\.?\s*S\.?\)?)\b'),
        ('UG', r'\b(?:Bachelor\s+of\s+Technology|Bachelor\s+of\s+Science|Bachelor\s+of\s+Engineering|Bachelor\s+of\s+Commerce|Bachelor\s+of\s+Arts|BCA|BBA|B\.?\s*Ed|\(?B\.?\s*Tech\.?\)?|\(?B\.?\s*Sc\.?\)?|\(?B\.?\s*E\.?\)?|\(?B\.?\s*S\.?\)?)\b'),
        ('Other', r'\b(?:12th|HSC|Higher\s+Secondary|Intermediate|10th|SSC|Matriculation|Secondary\s+School)\b')
    ]

    found = []
    seen_qtypes = set()
    for idx, line in enumerate(lines):
        if re.search(r'\b(advisor|thesis|supervisor|guide)\b', line, re.I):
            continue

        for qtype, pat in deg_specs:
            if re.search(pat, line, re.I) and qtype not in seen_qtypes:
                seen_qtypes.add(qtype)
                context = lines[max(0, idx-3):min(len(lines), idx+5)]

                stream = None
                sm = re.search(r'\bin\s+([A-Za-z\s&/,]+)', line, re.I)
                if sm:
                    stream = sm.group(1).strip()
                    stream = re.split(r'[,.]', stream)[0].strip()

                uni = None
                for c_line in context:
                    if c_line != line and re.search(r'\b(University|Institute|College|IIT|NIT|BITS|Vishwavidyalaya|School|Board)\b', c_line, re.I):
                        uni = c_line.strip(' ,.-')
                        break

                year = None
                for c_line in context:
                    ranges = re.findall(r'\b(19\d{2}|20\d{2})\b', c_line)
                    if ranges:
                        year = ranges[-1]
                        break

                found.append({
                    'qualification_type': qtype,
                    'degree': line,
                    'stream': stream,
                    'university': uni,
                    'year': year,
                    'cgpa': None
                })
                break
    return found

def extract_publications_from_text(text: str) -> List[Dict[str, Any]]:
    """Robust fallback extractor for research publications from resume text."""
    if not text:
        return []
    pub_match = re.search(
        r'(?:^|\n)\s*(?:Research\s+Publications|Publications|List of Publications|Selected Publications|Journals\s*(?:and|/)?\s*Conferences|Refereed\s+Articles)\b(.*?)(?:\n\s*(?:Awards|References|Skills|Projects|Workshops|Personal\s+Details|Declaration|Patents)|\Z)',
        text, re.I | re.S
    )
    if not pub_match:
        return []

    p_sec = pub_match.group(1)
    raw_entries = re.split(r'\n\s*(?:\[\d+\]|\d+[\.\)]|\(\d+\))\s*', p_sec)

    pubs = []
    for raw in raw_entries:
        entry = ' '.join([l.strip() for l in raw.split('\n') if l.strip()])
        if len(entry) < 25:
            continue
        if entry.lower() in ('journals/ conferences', 'journal publications:', 'conference publications:'):
            continue

        title = None
        tm = re.search(r'[\"“]([^\"”]{10,})[\"”]', entry)
        if tm:
            title = tm.group(1).strip()
        else:
            parts = re.split(r'[,.]\s+', entry)
            for p in parts:
                if len(p) > 20 and not any(k in p.lower() for k in ('ieee', 'springer', 'elsevier', 'vol.', 'pp.', 'author', 'publication')):
                    title = p.strip()
                    break
        if not title:
            title = entry[:100]

        year = None
        ym_parens = re.findall(r'\((\d{4})\)', entry)
        if ym_parens:
            year = int(ym_parens[-1])
        else:
            y_all = re.findall(r'\b(19[89]\d|20[0-3]\d)\b', entry)
            if y_all:
                year = int(y_all[-1])

        venue = None
        if 'IEEE' in entry:
            vm = re.search(r'(IEEE[^\,\;\n\(\)]+)', entry)
            if vm: venue = vm.group(1).strip()
        elif 'Elsevier' in entry:
            vm = re.search(r'(Elsevier[^\,\;\n\(\)]+)', entry)
            if vm: venue = vm.group(1).strip()
        elif 'Springer' in entry:
            vm = re.search(r'(Springer[^\,\;\n\(\)]+)', entry)
            if vm: venue = vm.group(1).strip()
        elif 'ACM' in entry:
            vm = re.search(r'(ACM[^\,\;\n\(\)]+)', entry)
            if vm: venue = vm.group(1).strip()
        elif re.search(r'\b(Journal|Conference|Transactions|Letters|Symposium)\b', entry, re.I):
            vm = re.search(r'([A-Za-z\s]+(?:Journal|Conference|Transactions|Letters|Symposium)[^\,\;\n\(\)]*)', entry, re.I)
            if vm: venue = vm.group(1).strip()

        pub_type = 'journal'
        if venue and any(k in venue.lower() for k in ('conference', 'proceedings', 'symposium', 'ncc', 'ic', 'workshop')):
            pub_type = 'conference'
        if venue and any(k in venue.lower() for k in ('journal', 'transactions', 'letters')):
            pub_type = 'journal'

        pubs.append({
            'publication_name': title,
            'venue_name': venue,
            'publication_year': year,
            'publication_type': pub_type
        })
    return pubs

class LLMExtractor:
    """
    Adaptive, Token-Aware, Recursive Resume Extraction Pipeline.
    Supports single-shot processing for normal resumes and recursive chunking + hierarchical LLM merge for large resumes.
    """
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()
        self.token_counter = TokenCounter()
        self.splitter = RecursiveTextSplitter(token_counter=self.token_counter)
        self.json_validator = JSONValidator()
        self.merger = HierarchicalMerger(provider=self.provider)
        self.chunk_cache = ChunkCache()
        self.retry_handler = RetryHandler()

    def clean_json_response(self, text: str) -> str:
        return self.json_validator.clean_json_response(text)

    def normalize_schema(self, raw_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize LLM output to the canonical schema regardless of how the small
        LLM structured its response.

        The LLM (especially small models like llama3.2) often returns a flat
        structure instead of the expected nested one, e.g.:
          - `name` / `full_name` instead of `personal_information.full_name`
          - `title` / `designation` instead of `personal_information.current_designation`
          - `academic` / `professional` at the top level instead of under `experience`
          - Missing `personal_information` wrapper entirely

        This normalizer detects and remaps all known alternative structures.
        """
        if not isinstance(raw_dict, dict):
            return raw_dict

        # ── 1. personal_information ─────────────────────────────────────────────
        p_info = raw_dict.get("personal_information")
        if not isinstance(p_info, dict):
            # LLM returned flat keys at top level
            p_info = {}

        # Remap common flat personal-info keys into the wrapper
        PINFO_ALIASES = {
            "full_name":            ["full_name", "name", "candidate_name", "applicant_name"],
            "current_designation":  ["current_designation", "designation", "title", "current_role",
                                     "current_position", "job_title", "position"],
            "email":                ["email", "email_address", "contact_email"],
            "phone":                ["phone", "phone_number", "mobile", "contact_number", "contact_phone"],
        }
        for canon_key, aliases in PINFO_ALIASES.items():
            if not p_info.get(canon_key):
                for alias in aliases:
                    # Check inside the p_info dict first, then top-level raw_dict
                    val = p_info.get(alias) or raw_dict.get(alias)
                    if val and str(val).strip().lower() not in ("null", "none", "n/a", ""):
                        p_info[canon_key] = val
                        break

        raw_dict["personal_information"] = p_info

        # ── 2. education ────────────────────────────────────────────────────────
        edu_list = raw_dict.get("education")
        if not isinstance(edu_list, list):
            edu_list = []

        # If the LLM stuffed education into `academic` under experience,
        # pick it up later; we'll only auto-convert obvious degree dicts here.
        # Remap field aliases inside each education item
        EDU_FIELD_ALIASES = {
            "qualification_type": ["qualification_type", "type", "level", "edu_type", "education_type"],
            "degree":             ["degree", "qualification", "degree_name", "program"],
            "stream":             ["stream", "specialization", "major", "field", "branch", "subject",
                                   "field_of_study"],
            "university":         ["university", "institution", "college", "school", "board",
                                   "university_name", "institute"],
            "year":               ["year", "graduation_year", "completion_year", "passing_year",
                                   "year_of_passing", "year_of_completion"],
            "cgpa":               ["cgpa", "gpa", "percentage", "grade", "marks", "score"],
        }
        normalized_edu = []
        for edu in edu_list:
            if not isinstance(edu, dict):
                continue
            norm_edu = dict(edu)
            for canon, aliases in EDU_FIELD_ALIASES.items():
                if not norm_edu.get(canon):
                    for alias in aliases:
                        val = edu.get(alias)
                        if val is not None:
                            norm_edu[canon] = val
                            break
            normalized_edu.append(norm_edu)
        raw_dict["education"] = normalized_edu

        # ── 3. experience ───────────────────────────────────────────────────────
        exp_val = raw_dict.get("experience")

        if isinstance(exp_val, dict):
            # Already a dict — ensure it has `academic` and `professional` keys
            # Also check for top-level `academic`/`professional` that weren't nested
            if not exp_val.get("academic") and not exp_val.get("professional"):
                # Dict exists but is empty or uses other keys — try top-level
                top_acad = raw_dict.get("academic") or []
                top_prof = raw_dict.get("professional") or raw_dict.get("industry") or []
                if isinstance(top_acad, list) or isinstance(top_prof, list):
                    exp_val = {
                        "academic": top_acad if isinstance(top_acad, list) else [],
                        "professional": top_prof if isinstance(top_prof, list) else [],
                    }
        elif isinstance(exp_val, list):
            # LLM returned a flat list — split by experience_type field
            acad = [x for x in exp_val if isinstance(x, dict) and
                    str(x.get("experience_type", "")).lower() in ("academic", "research")]
            prof = [x for x in exp_val if isinstance(x, dict) and
                    str(x.get("experience_type", "")).lower() in ("professional", "industry", "teaching")]
            if not acad and not prof:
                # No type tags — put everything in professional
                prof = [x for x in exp_val if isinstance(x, dict)]
            exp_val = {"academic": acad, "professional": prof}
        else:
            # experience key missing entirely — check for top-level academic/professional
            top_acad = raw_dict.get("academic") or []
            top_prof = raw_dict.get("professional") or raw_dict.get("industry") or []
            exp_val = {
                "academic": top_acad if isinstance(top_acad, list) else [],
                "professional": top_prof if isinstance(top_prof, list) else [],
            }

        # Normalise field aliases within each experience item
        EXP_FIELD_ALIASES = {
            "institution": ["institution", "organization", "company", "company_name", "employer",
                            "university", "college", "workplace"],
            "role":        ["role", "job_title", "designation", "title", "position"],
            "start_date":  ["start_date", "from", "from_date", "joining_date", "start"],
            "end_date":    ["end_date", "to", "to_date", "leaving_date", "end"],
            "duration_years": ["duration_years", "duration", "years", "tenure"],
            "description": ["description", "responsibilities", "duties", "summary"],
        }
        for section in ("academic", "professional"):
            items = exp_val.get(section) or []
            if not isinstance(items, list):
                items = []
            normed_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                norm_item = dict(item)
                for canon, aliases in EXP_FIELD_ALIASES.items():
                    if not norm_item.get(canon):
                        for alias in aliases:
                            val = item.get(alias)
                            if val is not None:
                                norm_item[canon] = val
                                break
                normed_items.append(norm_item)
            exp_val[section] = normed_items

        raw_dict["experience"] = exp_val

        # ── 4. publications ─────────────────────────────────────────────────────
        pub_list = raw_dict.get("publications")
        if not isinstance(pub_list, list):
            pub_list = []

        PUB_FIELD_ALIASES = {
            "publication_type": ["publication_type", "type", "pub_type", "category"],
            "publication_name": ["publication_name", "title", "paper_title", "name",
                                 "paper_name", "article_title"],
            "venue_name":       ["venue_name", "venue", "journal", "conference", "publisher",
                                 "journal_name", "conference_name", "published_in", "source"],
            "publication_year": ["publication_year", "year", "pub_year", "published_year",
                                 "year_published"],
        }
        normed_pubs = []
        for pub in pub_list:
            if not isinstance(pub, dict):
                continue
            norm_pub = dict(pub)
            for canon, aliases in PUB_FIELD_ALIASES.items():
                if not norm_pub.get(canon):
                    for alias in aliases:
                        val = pub.get(alias)
                        if val is not None:
                            norm_pub[canon] = val
                            break
            normed_pubs.append(norm_pub)
        raw_dict["publications"] = normed_pubs

        # ── 5. total_experience ─────────────────────────────────────────────────
        if not raw_dict.get("total_experience"):
            for alias in ("total_experience", "total_years", "years_of_experience",
                          "experience_years", "total_exp"):
                val = raw_dict.get(alias)
                if val is not None:
                    try:
                        raw_dict["total_experience"] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass

        return raw_dict

    def verify_and_clean_data(self, raw_dict: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        """
        Field-level validation, Anti-hallucination, Section-wise data validation,
        and fallback rescue post-processor.
        1. Validates fields against Pydantic schemas.
        2. Cleans prompt schema leaks (e.g. 'John Doe', '| null').
        3. Cross-section reconciliation:
           - Moves academic degrees from experience -> education.
           - Prunes software tools/skills (e.g. 'Tally Erp9') and null entries from experience.
           - Prunes corporate companies without degrees from education -> experience.
        4. Rescues candidate personal information (name, email, phone) if missing.
        5. Rescues educational qualifications (PhD, Post Doctoral, Master's, Bachelor's) from raw_text.
        6. Rescues research publications from raw_text if missing.
        7. Deduplicates and recalculates total_experience accurately.
        """
        if not isinstance(raw_dict, dict):
            raw_dict = {}

        raw_text_lower = raw_text.lower()

        # -------------------------------------------------------------
        # 1. Personal Information Validation & Rescue
        # -------------------------------------------------------------
        p_info = raw_dict.get("personal_information")
        if not isinstance(p_info, dict):
            p_info = {}

        # Sanitize personal info fields against template leaks
        for k in ["full_name", "current_designation", "email", "phone"]:
            p_info[k] = sanitize_string_value(p_info.get(k))

        # Rescue Name if missing or default
        if not p_info.get("full_name") or p_info.get("full_name").lower() in ("unknown candidate", "candidate", "profile"):
            rescued_name = extract_candidate_name_from_text(raw_text)
            if rescued_name:
                p_info["full_name"] = rescued_name

        # Rescue Email if missing
        if not p_info.get("email"):
            em_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", raw_text)
            if em_match:
                p_info["email"] = em_match.group(0)

        # Rescue Phone if missing
        if not p_info.get("phone"):
            ph_match = re.search(r"(?:\+?91[-.\s]?)?[6-9]\d{9}\b", raw_text)
            if ph_match:
                p_info["phone"] = ph_match.group(0)

        try:
            p_obj = PersonalInformation(**p_info)
            raw_dict["personal_information"] = p_obj.model_dump()
        except Exception:
            raw_dict["personal_information"] = p_info

        # -------------------------------------------------------------
        # 2. Section Cross-Contamination Reconciliation
        # -------------------------------------------------------------
        edu_list = raw_dict.get("education", [])
        if not isinstance(edu_list, list):
            edu_list = []

        exp_raw = raw_dict.get("experience", {})
        acad_raw = []
        prof_raw = []
        if isinstance(exp_raw, dict):
            acad_raw = exp_raw.get("academic", []) or []
            prof_raw = exp_raw.get("professional", []) or exp_raw.get("industry", []) or []
        elif isinstance(exp_raw, list):
            acad_raw = [x for x in exp_raw if isinstance(x, dict) and x.get("experience_type") == "academic"]
            prof_raw = [x for x in exp_raw if isinstance(x, dict) and x.get("experience_type") != "academic"]

        all_exp_items = acad_raw + prof_raw
        migrated_degrees_from_exp = []
        remaining_exp_items = []

        degree_pat = re.compile(
            r"\b(doctor of philosophy|\(?ph\.?\s*d\.?\)?|doctorate|\(?d\.?\s*phil\)?|"
            r"master of technology|\(?m\.?\s*tech\.?\)?|master of science|\(?m\.?\s*sc\.?\)?|"
            r"master of engineering|\(?m\.?\s*e\.?\)?|\(?m\.?\s*s\.?\)?|mca|mba|"
            r"bachelor of technology|\(?b\.?\s*tech\.?\)?|bachelor of science|\(?b\.?\s*sc\.?\)?|"
            r"bachelor of engineering|\(?b\.?\s*e\.?\)?|\(?b\.?\s*s\.?\)?|bca|bba|b\.?\s*com|"
            r"10th|12th|ssc|hsc|matriculation|secondary school|higher secondary)\b",
            re.I
        )
        faculty_pat = re.compile(r"\b(professor|lecturer|faculty|fellow|scholar|postdoc|jrf|srf|scientist|engineer|manager|officer|instructor|director|dean|hod)\b", re.I)

        for item in all_exp_items:
            if not isinstance(item, dict):
                continue
            r_str = str(item.get("role") or "").strip()
            i_str = str(item.get("institution") or item.get("company") or "").strip()

            # Check if this item is actually an educational degree study rather than a job
            is_deg = bool(degree_pat.search(r_str) or degree_pat.search(i_str))
            is_job = bool(faculty_pat.search(r_str))

            if is_deg and not is_job:
                # Migrate to education
                migrated_degrees_from_exp.append({
                    "qualification_type": infer_qualification_type(r_str or i_str, None),
                    "degree": r_str or i_str,
                    "stream": item.get("stream"),
                    "university": i_str if not degree_pat.search(i_str) else None,
                    "year": str(item.get("end_date") or item.get("start_date") or "")
                })
            else:
                remaining_exp_items.append(item)

        # Add migrated degrees to edu_list
        edu_list.extend(migrated_degrees_from_exp)

        # -------------------------------------------------------------
        # 3. Education Rescue from Raw Text
        # -------------------------------------------------------------
        has_phd_in_text = bool(re.search(r"\b(?:doctor of philosophy|\(?ph\.?\s*d\.?\)?|doctorate)\b", raw_text, re.I))
        has_phd_in_edu = any(
            "phd" in (e.get("qualification_type") or "").lower() or
            "phd" in (e.get("degree") or "").lower() or
            "doctor of philosophy" in (e.get("degree") or "").lower()
            for e in edu_list if isinstance(e, dict)
        )

        if len(edu_list) == 0 or (has_phd_in_text and not has_phd_in_edu):
            rescued_edus = extract_education_from_section(raw_text)
            for r_edu in rescued_edus:
                # Add if qualification type not yet represented
                q_t = r_edu.get("qualification_type")
                if not any((e.get("qualification_type") == q_t) for e in edu_list if isinstance(e, dict)):
                    edu_list.append(r_edu)

        # Clean and validate Education items
        cleaned_edu = []
        seen_edu_keys = set()
        for edu in edu_list:
            if not isinstance(edu, dict):
                continue
            deg_clean = sanitize_string_value(edu.get("degree"))
            uni_clean = sanitize_string_value(edu.get("university"))
            if not deg_clean and not uni_clean:
                continue

            # Anti-pollution: check if university is a commercial company without a degree
            if uni_clean and any(uni_clean.lower().endswith(suffix) for suffix in ("ltd", "ltd.", "limited", "pvt ltd", "pvt. ltd.", "inc", "corp", "llc")):
                if not deg_clean or faculty_pat.search(deg_clean):
                    # Corporate employment mistakenly placed in education
                    remaining_exp_items.append({
                        "institution": uni_clean,
                        "role": deg_clean or "Employee",
                        "start_date": edu.get("year"),
                        "end_date": None,
                        "duration_years": 0.0
                    })
                    continue

            # Sanitize stream
            stream_val = edu.get("stream")
            if stream_val and str(stream_val).lower() not in ("null", "none", "n/a", ""):
                s_str = str(stream_val).strip()
                words = [w.lower() for w in s_str.replace("&", " ").replace("/", " ").replace("-", " ").split() if len(w) >= 3 and w.lower() not in ("and", "the", "for", "in", "of", "engineering", "department", "technology", "science", "studies")]
                matched = any(w in raw_text_lower for w in words) if words else (s_str.lower() in raw_text_lower)
                if not matched:
                    edu["stream"] = None

            # Filter obvious non-academic items
            deg_lower = str(deg_clean or "").lower()
            is_postdoc = any(k in deg_lower for k in ("postdoc", "post-doc", "post doctoral", "post-doctoral", "pdf", "post doctorate"))
            if not is_postdoc and any(k in deg_lower for k in (
                "workshop", "webinar", "seminar", "fdp", "faculty development",
                "training program", "capstone project", "mini project", "final year project",
                "research paper", "patent published", "nptel", "aws certified", "azure certified", "cisco certified"
            )):
                continue

            edu["degree"] = deg_clean
            edu["university"] = uni_clean

            # Deduplication key
            key = f"{(deg_clean or '').lower()}:{(uni_clean or '').lower()}"
            if key != ":" and key in seen_edu_keys:
                continue
            seen_edu_keys.add(key)

            try:
                edu_obj = EducationItem(**edu)
                cleaned_edu.append(edu_obj.model_dump())
            except Exception as ex:
                cleaned_edu.append(edu)

        raw_dict["education"] = cleaned_edu

        # -------------------------------------------------------------
        # 4. Publications Validation & Rescue
        # -------------------------------------------------------------
        pub_list = raw_dict.get("publications", [])
        if not isinstance(pub_list, list):
            pub_list = []

        cleaned_pubs = []
        seen_pub_titles = set()
        for pub in pub_list:
            if not isinstance(pub, dict):
                continue
            p_name = sanitize_string_value(pub.get("publication_name"))
            if not p_name or "title of paper" in p_name.lower() or "actual paper" in p_name.lower():
                continue

            p_name_lower = p_name.lower()
            if any(k in p_name_lower for k in ("phd thesis", "ph.d thesis", "master's thesis", "m.tech thesis", "m.s. thesis", "b.tech project", "capstone project", "coursework")):
                continue

            pub["publication_name"] = p_name
            pub["venue_name"] = sanitize_string_value(pub.get("venue_name"))
            
            norm_title = re.sub(r'[\s"\'“”.,:;]+', ' ', p_name_lower).strip()
            if norm_title in seen_pub_titles:
                continue
            seen_pub_titles.add(norm_title)

            try:
                pub_obj = PublicationItem(**pub)
                cleaned_pubs.append(pub_obj.model_dump())
            except Exception as ex:
                cleaned_pubs.append(pub)

        # Rescue publications from raw text if list is empty
        if len(cleaned_pubs) == 0:
            rescued_pubs = extract_publications_from_text(raw_text)
            for r_pub in rescued_pubs:
                norm_title = re.sub(r'[\s"\'“”.,:;]+', ' ', (r_pub.get("publication_name") or "").lower()).strip()
                if norm_title and norm_title not in seen_pub_titles:
                    seen_pub_titles.add(norm_title)
                    try:
                        pub_obj = PublicationItem(**r_pub)
                        cleaned_pubs.append(pub_obj.model_dump())
                    except Exception:
                        cleaned_pubs.append(r_pub)

        raw_dict["publications"] = cleaned_pubs

        # -------------------------------------------------------------
        # 5. Experience Cleaning and Total Experience Calculation
        # -------------------------------------------------------------
        from backend.app.llm.experience_calculator import clean_and_calculate_experience_dict
        cleaned_exp_dict, total_exp = clean_and_calculate_experience_dict(
            remaining_exp_items,
            raw_total_exp=raw_dict.get("total_experience"),
            full_resume_text=raw_text
        )
        raw_dict["experience"] = cleaned_exp_dict
        raw_dict["total_experience"] = total_exp

        return raw_dict

    def extract_single_chunk(self, chunk_text: str, is_leaf: bool = False) -> Dict[str, Any]:
        """
        Extract structured JSON from a single text chunk with validation, retries, and repair.
        Raises ValueError when the model returns an empty/trivial response so the caller
        can fall back to smaller chunks.
        """
        if is_leaf:
            prompt = LEAF_EXTRACTION_USER_PROMPT_TEMPLATE.replace("{resume_text}", chunk_text)
        else:
            prompt = EXTRACTION_USER_PROMPT_TEMPLATE.replace("{resume_text}", chunk_text)
        
        system = EXTRACTION_SYSTEM_PROMPT

        def _call_llm() -> Dict[str, Any]:
            raw_response = self.provider.generate(prompt, system=system)
            try:
                parsed = self.json_validator.parse_json(raw_response)
            except Exception as parse_err:
                logger.warning(f"Leaf extraction parse failed: {parse_err}. Attempting LLM syntax repair...")
                parsed = self.json_validator.repair_with_llm(raw_response, self.provider)

            # Guard: if the model returned an empty / near-empty dict (e.g. `{}`),
            # treat it as a failure so the retry handler can try again or the
            # chunking path can take over.
            if not isinstance(parsed, dict) or len(parsed) == 0:
                raise ValueError(
                    "LLM returned an empty response `{}`. "
                    "The input chunk may be too large for the model context."
                )
            return parsed

        return self.retry_handler.execute_with_retry(_call_llm)

    def extract_leaf_chunk_adaptively(self, chunk: Chunk, doc_hash: str, model_name: str) -> Dict[str, Any]:
        """
        Extract leaf chunk with caching and automatic sub-splitting on timeout.
        """
        # 1. Check Chunk Cache
        cached_result = self.chunk_cache.get(doc_hash, chunk.text, model_name)
        if cached_result:
            return cached_result

        # 2. Extract with timeout fallback sub-splitting
        try:
            result = self.extract_single_chunk(chunk.text, is_leaf=True)
            result = self.normalize_schema(result)
            self.chunk_cache.set(doc_hash, chunk.text, model_name, result)
            return result
        except Exception as e:
            err_msg = str(e).lower()
            is_timeout = "timeout" in err_msg or "timed out" in err_msg or "readtimeout" in err_msg
            is_empty = "empty response" in err_msg
            
            # If timeout or empty response and chunk is large enough to split further
            if (is_timeout or is_empty) and chunk.token_count > 500:
                logger.warning(f"Leaf chunk {chunk.chunk_id} timed out ({chunk.token_count} tokens). Sub-splitting recursively...")
                sub_safe_limit = max(500, chunk.token_count // 2)
                sub_chunks = self.splitter.split_text(
                    chunk.text,
                    safe_limit=sub_safe_limit,
                    overlap_tokens=settings.OVERLAP_TOKENS // 2,
                    chunk_prefix=f"{chunk.chunk_id}_sub"
                )
                sub_results = []
                for sub_c in sub_chunks:
                    res = self.extract_leaf_chunk_adaptively(sub_c, doc_hash, model_name)
                    sub_results.append(res)
                merged_sub = self.merger.merge_all(sub_results)
                self.chunk_cache.set(doc_hash, chunk.text, model_name, merged_sub)
                return merged_sub
            else:
                raise e

    def extract_candidate_data(self, cleaned_resume_text: str, candidate_id: str = "CANDIDATE") -> Dict[str, Any]:
        """
        Main entry point for resume extraction.
        Adaptively chooses single LLM call or recursive chunking + hierarchical merge based on token count.
        """
        start_time = time.time()
        doc_hash = hashlib.sha256(cleaned_resume_text.encode('utf-8')).hexdigest()
        original_char_count = len(cleaned_resume_text)
        original_token_count = self.token_counter.count_tokens(cleaned_resume_text)
        model_name = getattr(self.provider, "model", settings.LLM_MODEL)

        logger.info(f"Starting Extraction for {candidate_id} | Chars: {original_char_count} | Tokens: {original_token_count}")

        llm_calls = 0
        retries = 0
        merge_calls = 0

        # ADAPTIVE PATHWAY: Small / Normal Resumes (within safe context limit)
        if original_token_count <= settings.SAFE_INPUT_TOKENS:
            print(f"[TOKEN-SPLIT] Candidate '{candidate_id}': Document size ({original_token_count:,} tokens) <= SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS:,}). Single LLM call pathway (no split required).", flush=True)
            logger.info(f"{candidate_id}: Token count ({original_token_count}) <= SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS}). Using single LLM call.")
            try:
                result = self.extract_single_chunk(cleaned_resume_text, is_leaf=False)
                result = self.normalize_schema(result)
                result = self.verify_and_clean_data(result, cleaned_resume_text)
                elapsed = time.time() - start_time
                logger.info(f"SUMMARY [{candidate_id}] | tokens={original_token_count} | chunks=1 | chunk_sizes=[{original_token_count}] | llm_calls=1 | status=SUCCESS | time={elapsed:.2f}s")
                return result
            except Exception as e:
                print(f"[TOKEN-SPLIT] Single-shot extraction failed for candidate {candidate_id}: {e}. Falling back to chunked extraction.", flush=True)
                logger.warning(f"Single-shot extraction failed for candidate {candidate_id}: {e}. Falling back to chunked extraction.")
                # Fall through to chunked extraction below

        # ADAPTIVE PATHWAY: Large / Long Resumes (exceeding safe context limit)
        print(f"\n[TOKEN-SPLIT] Candidate '{candidate_id}': Document size ({original_token_count:,} tokens) > SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS:,}).", flush=True)
        print(f"[TOKEN-SPLIT] Initiating Recursive Splitting & Hierarchical Merging...", flush=True)
        logger.info(f"{candidate_id}: Token count ({original_token_count}) > SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS}). Initiating Recursive Splitting & Merging.")

        chunks = self.splitter.split_text(
            cleaned_resume_text,
            safe_limit=settings.SAFE_INPUT_TOKENS,
            overlap_tokens=settings.OVERLAP_TOKENS,
            chunk_prefix=f"{candidate_id}_chk",
            verbose=True
        )
        chunk_sizes = [c.token_count for c in chunks]
        print(f"[TOKEN-SPLIT] Candidate '{candidate_id}' split into {len(chunks)} leaf chunks | Sizes: {chunk_sizes}", flush=True)
        logger.info(f"{candidate_id}: Split into {len(chunks)} leaf chunks | Sizes: {chunk_sizes}")

        partial_results = []
        for idx, chunk in enumerate(chunks):
            print(f"[TOKEN-SPLIT] -> [{idx+1}/{len(chunks)}] Extracting Leaf Chunk '{chunk.chunk_id}' ({chunk.token_count:,} tokens, doc span {chunk.start_char:,}..{chunk.end_char:,})...", flush=True)
            logger.info(f"{candidate_id}: Extracting Chunk {idx+1}/{len(chunks)} ({chunk.chunk_id}) - {chunk.token_count} tokens")
            leaf_json = self.extract_leaf_chunk_adaptively(chunk, doc_hash, model_name)
            partial_results.append(leaf_json)
            llm_calls += 1

        # Hierarchical Merging of Partial JSON Outputs
        print(f"[TOKEN-SPLIT] Hierarchically merging {len(partial_results)} partial JSON results...", flush=True)
        logger.info(f"{candidate_id}: Hierarchically merging {len(partial_results)} partial JSON results...")
        final_json = self.merger.merge_all(partial_results)
        final_json = self.normalize_schema(final_json)
        final_json = self.verify_and_clean_data(final_json, cleaned_resume_text)
        merge_calls = len(partial_results) - 1 if len(partial_results) > 1 else 0

        elapsed = time.time() - start_time
        summary_msg = (
            f"SUMMARY [{candidate_id}] | original_tokens={original_token_count:,} | chunks={len(chunks)} | "
            f"chunk_sizes={chunk_sizes} | overlap={settings.OVERLAP_TOKENS} | llm_calls={llm_calls} | "
            f"merge_calls={merge_calls} | status=SUCCESS | time={elapsed:.2f}s"
        )
        print(f"[TOKEN-SPLIT] ✓ {summary_msg}\n", flush=True)
        logger.info(summary_msg)

        return final_json

