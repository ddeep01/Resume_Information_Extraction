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

from backend.app.schemas.candidate import EducationItem, PersonalInformation, PublicationItem

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
        Field-level validation & Anti-hallucination post-processor.
        1. Validates fields against Pydantic schemas.
        2. Cleans prompt schema leaks (e.g., 'PhD | M.Tech...' -> 'PhD').
        3. Verifies 'stream' against raw text to prevent hallucinated departments.
        """
        if not raw_dict:
            return raw_dict
        
        raw_text_lower = raw_text.lower()

        # Clean Education items & verify stream anti-hallucination
        edu_list = raw_dict.get("education", [])
        if isinstance(edu_list, list):
            cleaned_edu = []
            for edu in edu_list:
                if not isinstance(edu, dict):
                    continue
                # Sanitize stream against hallucination
                stream_val = edu.get("stream")
                if stream_val and str(stream_val).lower() not in ("null", "none", "n/a", ""):
                    s_str = str(stream_val).strip()
                    # Check if stream or its core words exist in raw resume text
                    words = [w.lower() for w in s_str.replace("&", " ").replace("/", " ").replace("-", " ").split() if len(w) >= 3 and w.lower() not in ("and", "the", "for", "in", "of", "engineering", "department", "technology", "science", "studies")]
                    matched = any(w in raw_text_lower for w in words) if words else (s_str.lower() in raw_text_lower)
                    if not matched:
                        logger.warning(f"Anti-Hallucination: Stripped unmentioned stream '{s_str}' from degree '{edu.get('degree')}'")
                        edu["stream"] = None
                
                u_name = str(edu.get("university") or "").strip()
                if "name of college or university" in u_name.lower():
                    continue

                # Filter out obvious non-academic items (certifications, workshops, seminars, training, projects, publications)
                deg_lower = str(edu.get("degree") or "").lower().strip()
                is_postdoc = any(k in deg_lower for k in ("postdoc", "post-doc", "post doctoral", "post-doctoral", "pdf", "post doctorate"))
                if not is_postdoc:
                    if any(k in deg_lower for k in (
                        "workshop", "webinar", "seminar", "fdp", "faculty development",
                        "training program", "capstone project", "mini project", "final year project",
                        "research paper", "patent published", "nptel", "aws certified", "azure certified", "cisco certified"
                    )):
                        logger.warning(f"Anti-Pollution: Dropped non-academic item '{deg_lower}' from education list")
                        continue

                # Run through EducationItem Pydantic schema validation
                try:
                    edu_obj = EducationItem(**edu)
                    cleaned_edu.append(edu_obj.model_dump())
                except Exception as ex:
                    logger.debug(f"Education item pydantic validation fallback: {ex}")
                    cleaned_edu.append(edu)
            raw_dict["education"] = cleaned_edu

        # Clean Publications against template placeholder leaks and validate with PublicationItem
        from backend.app.schemas.candidate import PublicationItem
        pub_list = raw_dict.get("publications", [])
        if isinstance(pub_list, list):
            cleaned_pubs = []
            for pub in pub_list:
                if not isinstance(pub, dict):
                    continue
                p_name = str(pub.get("publication_name") or "").strip()
                if not p_name or "title of paper or patent" in p_name.lower() or "actual paper" in p_name.lower():
                    continue

                # Filter obvious thesis/dissertation, student project, or coursework titles
                p_name_lower = p_name.lower()
                if any(k in p_name_lower for k in ("phd thesis", "ph.d thesis", "master's thesis", "m.tech thesis", "m.s. thesis", "b.tech project", "capstone project", "coursework")):
                    continue

                try:
                    pub_obj = PublicationItem(**pub)
                    cleaned_pubs.append(pub_obj.model_dump())
                except Exception as ex:
                    logger.debug(f"Publication item validation fallback: {ex}")
                    cleaned_pubs.append(pub)
            raw_dict["publications"] = cleaned_pubs

        # Clean Personal Info
        if "personal_information" in raw_dict and isinstance(raw_dict["personal_information"], dict):
            try:
                p_obj = PersonalInformation(**raw_dict["personal_information"])
                raw_dict["personal_information"] = p_obj.model_dump()
            except Exception:
                pass

        # Clean Experience items and calculate candidate total_experience
        from backend.app.llm.experience_calculator import clean_and_calculate_experience_dict
        exp_raw = raw_dict.get("experience")
        cleaned_exp_dict, total_exp = clean_and_calculate_experience_dict(
            exp_raw,
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
            logger.info(f"{candidate_id}: Token count ({original_token_count}) <= SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS}). Using single LLM call.")
            try:
                result = self.extract_single_chunk(cleaned_resume_text, is_leaf=False)
                result = self.normalize_schema(result)
                result = self.verify_and_clean_data(result, cleaned_resume_text)
                elapsed = time.time() - start_time
                logger.info(f"SUMMARY [{candidate_id}] | tokens={original_token_count} | chunks=1 | chunk_sizes=[{original_token_count}] | llm_calls=1 | status=SUCCESS | time={elapsed:.2f}s")
                return result
            except Exception as e:
                logger.warning(f"Single-shot extraction failed for candidate {candidate_id}: {e}. Falling back to chunked extraction.")
                # Fall through to chunked extraction below

        # ADAPTIVE PATHWAY: Large / Long Resumes (exceeding safe context limit)
        logger.info(f"{candidate_id}: Token count ({original_token_count}) > SAFE_INPUT_TOKENS ({settings.SAFE_INPUT_TOKENS}). Initiating Recursive Splitting & Merging.")

        chunks = self.splitter.split_text(
            cleaned_resume_text,
            safe_limit=settings.SAFE_INPUT_TOKENS,
            overlap_tokens=settings.OVERLAP_TOKENS,
            chunk_prefix=f"{candidate_id}_chk"
        )
        chunk_sizes = [c.token_count for c in chunks]
        logger.info(f"{candidate_id}: Split into {len(chunks)} leaf chunks | Sizes: {chunk_sizes}")

        partial_results = []
        for idx, chunk in enumerate(chunks):
            logger.info(f"{candidate_id}: Extracting Chunk {idx+1}/{len(chunks)} ({chunk.chunk_id}) - {chunk.token_count} tokens")
            leaf_json = self.extract_leaf_chunk_adaptively(chunk, doc_hash, model_name)
            partial_results.append(leaf_json)
            llm_calls += 1

        # Hierarchical Merging of Partial JSON Outputs
        logger.info(f"{candidate_id}: Hierarchically merging {len(partial_results)} partial JSON results...")
        final_json = self.merger.merge_all(partial_results)
        final_json = self.normalize_schema(final_json)
        final_json = self.verify_and_clean_data(final_json, cleaned_resume_text)
        merge_calls = len(partial_results) - 1 if len(partial_results) > 1 else 0

        elapsed = time.time() - start_time
        logger.info(
            f"SUMMARY [{candidate_id}] | original_tokens={original_token_count} | chunks={len(chunks)} | "
            f"chunk_sizes={chunk_sizes} | overlap={settings.OVERLAP_TOKENS} | llm_calls={llm_calls} | "
            f"merge_calls={merge_calls} | status=SUCCESS | time={elapsed:.2f}s"
        )

        return final_json

