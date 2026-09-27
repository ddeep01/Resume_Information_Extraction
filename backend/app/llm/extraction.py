import json
import re
import logging
from typing import Dict, Any, Optional

from backend.app.config import settings
from backend.app.llm.base import LLMProvider
from backend.app.llm.ollama_provider import OllamaProvider
from backend.app.llm.remote_provider import OpenAIProvider, MockFallbackProvider
from backend.app.llm.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE

logger = logging.getLogger("LLMExtractor")

def get_llm_provider() -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "ollama":
        try:
            return OllamaProvider()
        except Exception as e:
            logger.warning(f"Ollama provider failed to initialize ({e}). Falling back to Mock/Fallback.")
            return MockFallbackProvider()
    elif provider_name == "openai":
        try:
            return OpenAIProvider()
        except Exception as e:
            logger.warning(f"OpenAI provider failed ({e}). Falling back to Mock/Fallback.")
            return MockFallbackProvider()
    else:
        return MockFallbackProvider()

class LLMExtractor:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()
        self.fallback_provider = MockFallbackProvider()

    def clean_json_response(self, text: str) -> str:
        text = text.strip()
        # Remove ```json ... ``` codeblocks
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    def extract_candidate_data(self, cleaned_resume_text: str) -> Dict[str, Any]:
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(resume_text=cleaned_resume_text)
        system = EXTRACTION_SYSTEM_PROMPT

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                raw_response = self.provider.generate(prompt, system=system)
                cleaned_response = self.clean_json_response(raw_response)
                parsed_json = json.loads(cleaned_response)
                if isinstance(parsed_json, dict):
                    return parsed_json
            except Exception as e:
                logger.warning(f"LLM extraction attempt {attempt+1} failed: {e}")

        # Fallback to Mock / Heuristic provider to ensure business continuity
        logger.info("Using fallback parser for candidate extraction.")
        fallback_response = self.fallback_provider.generate(prompt, system=system)
        return json.loads(self.clean_json_response(fallback_response))
