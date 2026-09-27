import requests
import json
import re
import logging
from typing import Optional
from backend.app.llm.base import LLMProvider
from backend.app.config import settings

logger = logging.getLogger("RemoteProvider")

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model or "gpt-3.5-turbo"

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0
        }
        try:
            res = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise RuntimeError(f"OpenAI Provider error: {e}")


