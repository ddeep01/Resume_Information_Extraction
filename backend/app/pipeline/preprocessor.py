import re
import unicodedata
import logging

logger = logging.getLogger("TextPreprocessor")

class ResumeTextCleaner:
    def __init__(self):
        self.unicode_map = {
            "ﬁ": "fi", "ﬂ": "fl", "“": '"', "”": '"', "‘": "'", "’": "'",
            "–": "-", "—": "-", "−": "-", "•": "-", "●": "-", "▪": "-",
            "■": "-", "◦": "-", "►": "-", "➤": "-", "✓": "-", "✔": "-",
            "\u00A0": " ", "\u200B": "", "\ufeff": "",
        }

    def clean(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        # 1. Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        for old, new in self.unicode_map.items():
            text = text.replace(old, new)

        # 2. Control characters removal
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)

        # 3. Line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Fix hyphenated word wrapping: e.g. "com-\nputer" -> "computer"
        text = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", text)

        # 5. Tabs to spaces
        text = text.replace("\t", " ")

        # 6. Normalize multiple spaces
        text = re.sub(r"[ ]{2,}", " ", text)

        # 7. Strip trailing spaces per line
        lines = [line.rstrip() for line in text.splitlines()]
        text = "\n".join(lines)

        # 8. Collapse 3+ consecutive newlines to 2 newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
