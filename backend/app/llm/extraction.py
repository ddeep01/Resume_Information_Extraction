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
            res = requests.get(f"{settings.LLM_BASE_URL.rstrip('/')}/api/tags", timeout=2)
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

    def verify_and_clean_data(self, raw_dict: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
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
                
                # Run through EducationItem Pydantic schema validation
                try:
                    edu_obj = EducationItem(**edu)
                    cleaned_edu.append(edu_obj.model_dump())
                except Exception as ex:
                    logger.debug(f"Education item pydantic validation fallback: {ex}")
                    cleaned_edu.append(edu)
            raw_dict["education"] = cleaned_edu

        # Clean Personal Info
        if "personal_information" in raw_dict and isinstance(raw_dict["personal_information"], dict):
            try:
                p_obj = PersonalInformation(**raw_dict["personal_information"])
                raw_dict["personal_information"] = p_obj.model_dump()
            except Exception:
                pass

        return raw_dict

    def extract_single_chunk(self, chunk_text: str, is_leaf: bool = False) -> Dict[str, Any]:
        """
        Extract structured JSON from a single text chunk with validation, retries, and repair.
        """
        if is_leaf:
            prompt = LEAF_EXTRACTION_USER_PROMPT_TEMPLATE.replace("{resume_text}", chunk_text)
        else:
            prompt = EXTRACTION_USER_PROMPT_TEMPLATE.replace("{resume_text}", chunk_text)
        
        system = EXTRACTION_SYSTEM_PROMPT

        def _call_llm() -> Dict[str, Any]:
            raw_response = self.provider.generate(prompt, system=system)
            try:
                return self.json_validator.parse_json(raw_response)
            except Exception as parse_err:
                logger.warning(f"Leaf extraction parse failed: {parse_err}. Attempting LLM syntax repair...")
                return self.json_validator.repair_with_llm(raw_response, self.provider)

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
            self.chunk_cache.set(doc_hash, chunk.text, model_name, result)
            return result
        except Exception as e:
            err_msg = str(e).lower()
            is_timeout = "timeout" in err_msg or "timed out" in err_msg or "readtimeout" in err_msg
            
            # If timeout and chunk is large enough to split further
            if is_timeout and chunk.token_count > 1000:
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
                result = self.verify_and_clean_data(result, cleaned_resume_text)
                elapsed = time.time() - start_time
                logger.info(f"SUMMARY [{candidate_id}] | tokens={original_token_count} | chunks=1 | chunk_sizes=[{original_token_count}] | llm_calls=1 | status=SUCCESS | time={elapsed:.2f}s")
                return result
            except Exception as e:
                logger.error(f"Single-shot extraction failed for candidate {candidate_id}: {e}")
                raise e

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
        final_json = self.verify_and_clean_data(final_json, cleaned_resume_text)
        merge_calls = len(partial_results) - 1 if len(partial_results) > 1 else 0

        elapsed = time.time() - start_time
        logger.info(
            f"SUMMARY [{candidate_id}] | original_tokens={original_token_count} | chunks={len(chunks)} | "
            f"chunk_sizes={chunk_sizes} | overlap={settings.OVERLAP_TOKENS} | llm_calls={llm_calls} | "
            f"merge_calls={merge_calls} | status=SUCCESS | time={elapsed:.2f}s"
        )

        return final_json

