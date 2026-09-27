import json
import re
import logging
import requests
from typing import Dict, Any, Optional

from backend.app.config import settings
from backend.app.llm.base import LLMProvider
from backend.app.llm.ollama_provider import OllamaProvider
from backend.app.llm.remote_provider import OpenAIProvider
from backend.app.llm.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE

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

class LLMExtractor:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def clean_json_response(self, text: str) -> str:
        text = text.strip()
        # Remove ```json ... ``` codeblocks
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE).strip()
        # Extract JSON object between { and } if LLM included conversational text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        # Fix trailing commas before closing braces/brackets
        text = re.sub(r",\s*([\}\]])", r"\1", text)
        return text.strip()

    def extract_candidate_data(self, cleaned_resume_text: str) -> Dict[str, Any]:
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(resume_text=cleaned_resume_text)
        system = EXTRACTION_SYSTEM_PROMPT

        # Always execute via LLM
        raw_response = self.provider.generate(prompt, system=system)
        cleaned_response = self.clean_json_response(raw_response)
        
        try:
            parsed_json = json.loads(cleaned_response)
        except Exception as e:
            logger.error(f"JSON parsing failed for candidate extraction: {e}. Raw response snippet: {raw_response[:300]!r}")
            raise ValueError(f"LLM output could not be parsed as JSON: {e}")
        
        if not isinstance(parsed_json, dict):
            raise ValueError(f"LLM output is not a valid JSON dictionary: {cleaned_response[:100]}")
            
        return parsed_json
