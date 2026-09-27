import re
import logging
from typing import Optional

logger = logging.getLogger("TokenCounter")

class TokenCounter:
    """
    Model-compatible token counter with Tiktoken support and fallback estimation.
    """
    def __init__(self, model_name: str = "cl100k_base"):
        self.encoder = None
        try:
            import tiktoken
            try:
                self.encoder = tiktoken.encoding_for_model(model_name)
            except Exception:
                self.encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.debug("tiktoken package not installed. Using character/word estimation fallback for token counting.")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Tiktoken encoding failed: {e}. Falling back to character estimation.")
        
        # Fallback estimation for English technical/resume text:
        # Standard Llama/GPT tokenizers average ~3.8 to 4.0 characters per token.
        # We also factor in word count (~1.3 tokens per word).
        words = len(re.findall(r'\w+', text))
        chars = len(text)
        token_est_from_chars = int(chars / 3.8)
        token_est_from_words = int(words * 1.3)
        return max(token_est_from_chars, token_est_from_words, 1)

    def estimate_chars_for_tokens(self, token_count: int) -> int:
        """
        Estimate character count corresponding to given token count.
        """
        return int(token_count * 3.8)
