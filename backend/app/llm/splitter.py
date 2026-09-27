import re
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from backend.app.llm.token_counter import TokenCounter
from backend.app.config import settings

logger = logging.getLogger("TextSplitter")

@dataclass
class Chunk:
    chunk_id: str
    text: str
    token_count: int
    start_char: int
    end_char: int

SECTION_HEADER_PATTERN = re.compile(
    r'\n\s*(?:[A-Z\s]{3,30}|EDUCATION|WORK\s+EXPERIENCE|ACADEMIC\s+EXPERIENCE|INDUSTRY\s+EXPERIENCE|EXPERIENCE|PUBLICATIONS|PROJECTS|RESEARCH|PATENTS|CERTIFICATIONS|SKILLS|AWARDS|HONORS|SUMMARY|PROFILE)\s*(?::|\n)',
    re.IGNORECASE
)
BULLET_PATTERN = re.compile(r'\n\s*(?:[-*•]|\d+\.)\s+')
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')

class RecursiveTextSplitter:
    """
    Adaptive, boundary-aware, recursive text splitter with token overlap control.
    """
    def __init__(self, token_counter: Optional[TokenCounter] = None):
        self.token_counter = token_counter or TokenCounter()

    def find_best_split_point(self, text: str, target_char_idx: int, window_chars: int = 4000) -> int:
        """
        Find natural semantic split boundary near target_char_idx within +/- window_chars.
        Priority order:
        1. Section boundary
        2. Paragraph boundary
        3. Bullet item boundary
        4. Sentence boundary
        5. Line boundary
        6. Target char fallback
        """
        text_len = len(text)
        search_start = max(0, target_char_idx - window_chars)
        search_end = min(text_len, target_char_idx + window_chars)
        search_region = text[search_start:search_end]

        # 1. Section boundary
        section_matches = list(SECTION_HEADER_PATTERN.finditer(search_region))
        if section_matches:
            # Pick section match closest to target_char_idx
            best_match = min(section_matches, key=lambda m: abs((search_start + m.start()) - target_char_idx))
            return search_start + best_match.start()

        # 2. Paragraph boundary (\n\n)
        para_indices = [search_start + m.start() for m in re.finditer(r'\n\s*\n', search_region)]
        if para_indices:
            best_idx = min(para_indices, key=lambda idx: abs(idx - target_char_idx))
            return best_idx

        # 3. Bullet boundary
        bullet_indices = [search_start + m.start() for m in BULLET_PATTERN.finditer(search_region)]
        if bullet_indices:
            best_idx = min(bullet_indices, key=lambda idx: abs(idx - target_char_idx))
            return best_idx

        # 4. Sentence boundary
        sentence_indices = [search_start + m.start() for m in SENTENCE_PATTERN.finditer(search_region)]
        if sentence_indices:
            best_idx = min(sentence_indices, key=lambda idx: abs(idx - target_char_idx))
            return best_idx

        # 5. Line boundary (\n)
        line_indices = [search_start + m.start() for m in re.finditer(r'\n', search_region)]
        if line_indices:
            best_idx = min(line_indices, key=lambda idx: abs(idx - target_char_idx))
            return best_idx

        # 6. Fallback
        return target_char_idx

    def _split_into_two(
        self,
        text: str,
        safe_limit: int,
        overlap_tokens: int,
        start_offset: int = 0
    ) -> Tuple[Tuple[str, int, int], Tuple[str, int, int]]:
        """
        Split text into left and right sub-texts with overlap near the midpoint.
        """
        total_tokens = self.token_counter.count_tokens(text)
        total_chars = len(text)

        # Estimate midpoint in characters
        mid_ratio = 0.5
        target_char_idx = int(total_chars * mid_ratio)
        
        split_idx = self.find_best_split_point(text, target_char_idx)
        
        # Ensure split_idx is valid and not at exact boundaries 0 or total_chars
        if split_idx <= 100 or split_idx >= total_chars - 100:
            split_idx = total_chars // 2

        # Left piece: 0 to split_idx
        left_text = text[:split_idx]

        # Right piece with overlap: start back from split_idx by overlap_tokens equivalent
        overlap_chars = self.token_counter.estimate_chars_for_tokens(overlap_tokens)
        right_start_raw = max(0, split_idx - overlap_chars)
        
        # Refine right_start to a clean boundary near right_start_raw
        right_start = self.find_best_split_point(text, right_start_raw, window_chars=500)
        if right_start >= split_idx:
            right_start = max(0, split_idx - overlap_chars)

        right_text = text[right_start:]

        left_range = (left_text, start_offset, start_offset + split_idx)
        right_range = (right_text, start_offset + right_start, start_offset + total_chars)

        return left_range, right_range

    def split_text(
        self,
        text: str,
        safe_limit: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        chunk_prefix: str = "chunk",
        start_offset: int = 0
    ) -> List[Chunk]:
        """
        Recursively split text into overlapping chunks until every chunk <= safe_limit.
        """
        safe_limit = safe_limit or settings.SAFE_INPUT_TOKENS
        overlap_tokens = overlap_tokens or settings.OVERLAP_TOKENS

        token_count = self.token_counter.count_tokens(text)

        # Base case: text fits within safe limit
        if token_count <= safe_limit:
            return [
                Chunk(
                    chunk_id=chunk_prefix,
                    text=text,
                    token_count=token_count,
                    start_char=start_offset,
                    end_char=start_offset + len(text)
                )
            ]

        # Recursive case: split into left and right
        left_item, right_item = self._split_into_two(text, safe_limit, overlap_tokens, start_offset=start_offset)
        
        left_text, left_start, left_end = left_item
        right_text, right_start, right_end = right_item

        # Guard against infinite recursion if split produced identical sizes
        if len(left_text) >= len(text) or len(right_text) >= len(text):
            mid = len(text) // 2
            left_text = text[:mid]
            right_text = text[max(0, mid - 500):]
            left_start, left_end = start_offset, start_offset + len(left_text)
            right_start, right_end = start_offset + max(0, mid - 500), start_offset + len(text)

        left_chunks = self.split_text(
            left_text,
            safe_limit=safe_limit,
            overlap_tokens=overlap_tokens,
            chunk_prefix=f"{chunk_prefix}_L",
            start_offset=left_start
        )
        right_chunks = self.split_text(
            right_text,
            safe_limit=safe_limit,
            overlap_tokens=overlap_tokens,
            chunk_prefix=f"{chunk_prefix}_R",
            start_offset=right_start
        )

        return left_chunks + right_chunks
