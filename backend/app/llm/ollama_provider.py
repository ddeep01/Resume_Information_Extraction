import requests
import logging
from typing import Optional
from backend.app.llm.base import LLMProvider
from backend.app.config import settings

logger = logging.getLogger("OllamaProvider")

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = None, model: str = None, temperature: float = 0.0):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama generation failed at {url}: {e}")
            raise RuntimeError(f"Ollama API request error: {e}")
