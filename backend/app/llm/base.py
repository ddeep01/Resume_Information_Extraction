from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate completion for prompt and optional system message.
        Must return raw output string (preferably JSON).
        """
        pass
