"""Resume text cleaner.

Performs deterministic text cleaning on extracted resume text.
Never removes useful resume information.

Pipeline:
Extracted Text -> Unicode Normalization -> Control Character Removal ->
Normalize Line Endings -> Fix Hyphenated Words -> Normalize Tabs ->
Normalize Spaces -> Normalize Bullet Symbols -> Trim Trailing Spaces ->
Collapse Excess Blank Lines -> Clean Text
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data" / "extracted_text"
OUTPUT_DIR = ROOT / "data" / "cleaned_text"
REPORT_DIR = ROOT / "backend" / "text_cleaning" / "report"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("ResumeCleaner")


@dataclass
class CleanerConfig:
    normalize_unicode: bool = True
    remove_control_characters: bool = True
    normalize_line_endings: bool = True
    fix_hyphenated_words: bool = True
    normalize_tabs: bool = True
    normalize_spaces: bool = True
    normalize_bullets: bool = True
    trim_trailing_spaces: bool = True
    collapse_blank_lines: bool = True


@dataclass
class CleaningStatistics:
    documents: int = 0
    successful: int = 0
    failed: int = 0
    original_characters: int = 0
    cleaned_characters: int = 0
    unicode_replacements: int = 0
    hyphen_fixes: int = 0
    control_characters_removed: int = 0
    bullet_normalized: int = 0
    spaces_removed: int = 0
    blank_lines_removed: int = 0

    def report(self):
        ratio = 0

        if self.original_characters:
            ratio = round(self.cleaned_characters / self.original_characters, 4)

        return {
            "documents": self.documents,
            "successful": self.successful,
            "failed": self.failed,
            "original_characters": self.original_characters,
            "cleaned_characters": self.cleaned_characters,
            "compression_ratio": ratio,
            "unicode_replacements": self.unicode_replacements,
            "hyphen_fixes": self.hyphen_fixes,
            "control_characters_removed": self.control_characters_removed,
            "bullet_normalized": self.bullet_normalized,
            "spaces_removed": self.spaces_removed,
            "blank_lines_removed": self.blank_lines_removed,
        }


class TextCleaner:

    def __init__(self, config: CleanerConfig | None = None):
        self.config = config or CleanerConfig()
        self.stats = CleaningStatistics()

        self.unicode_map = {
            "ﬁ": "fi",
            "ﬂ": "fl",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "–": "-",
            "—": "-",
            "−": "-",
            "•": "-",
            "●": "-",
            "▪": "-",
            "■": "-",
            "◦": "-",
            "►": "-",
            "➤": "-",
            "✓": "-",
            "✔": "-",
            "\u00A0": " ",
            "\u200B": "",
            "\ufeff": "",
        }

    def normalize_unicode(self, text: str) -> str:
        if not self.config.normalize_unicode:
            return text

        text = unicodedata.normalize("NFKC", text)

        for old, new in self.unicode_map.items():
            count = text.count(old)

            if count:
                self.stats.unicode_replacements += count
                text = text.replace(old, new)

        return text

    def remove_control_characters(self, text: str) -> str:
        if not self.config.remove_control_characters:
            return text

        matches = re.findall(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", text)
        self.stats.control_characters_removed += len(matches)

        return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)

    def normalize_line_endings(self, text: str) -> str:
        if not self.config.normalize_line_endings:
            return text

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        return text

    def fix_hyphenated_words(self, text: str) -> str:
        if not self.config.fix_hyphenated_words:
            return text

        pattern = r"([A-Za-z])-\n([A-Za-z])"
        matches = re.findall(pattern, text)
        self.stats.hyphen_fixes += len(matches)

        return re.sub(pattern, r"\1\2", text)

    def normalize_tabs(self, text: str) -> str:
        if not self.config.normalize_tabs:
            return text

        return text.replace("\t", " ")

    def normalize_spaces(self, text: str) -> str:
        if not self.config.normalize_spaces:
            return text

        before = len(text)
        text = re.sub(r"[ ]{2,}", " ", text)
        after = len(text)

        self.stats.spaces_removed += (before - after)

        return text

    def normalize_bullets(self, text: str) -> str:
        if not self.config.normalize_bullets:
            return text

        total = 0

        bullets = ["•", "●", "▪", "■", "◦", "►", "➤", "✓", "✔"]

        for bullet in bullets:
            count = text.count(bullet)

            if count:
                total += count
                text = text.replace(bullet, "-")

        self.stats.bullet_normalized += total

        return text

    def trim_trailing_spaces(self, text: str) -> str:
        if not self.config.trim_trailing_spaces:
            return text

        lines = [line.rstrip() for line in text.splitlines()]

        return "\n".join(lines)

    def collapse_blank_lines(self, text: str) -> str:
        if not self.config.collapse_blank_lines:
            return text

        before = text.count("\n\n\n")
        text = re.sub(r"\n{3,}", "\n\n", text)

        self.stats.blank_lines_removed += before

        return text

    def clean(self, text: str) -> str:
        self.stats.documents += 1
        self.stats.original_characters += len(text)

        text = self.normalize_unicode(text)
        text = self.remove_control_characters(text)
        text = self.normalize_line_endings(text)
        text = self.fix_hyphenated_words(text)
        text = self.normalize_tabs(text)
        text = self.normalize_spaces(text)
        text = self.normalize_bullets(text)
        text = self.trim_trailing_spaces(text)
        text = self.collapse_blank_lines(text)

        self.stats.cleaned_characters += len(text)
        self.stats.successful += 1

        return text


class ResumeCleaner:

    def __init__(self):
        self.cleaner = TextCleaner()

    def clean_file(self, input_file: Path, output_file: Path) -> None:
        logger.info(f"Cleaning : {input_file.name}")

        try:
            text = input_file.read_text(encoding="utf-8", errors="ignore")
            cleaned = self.cleaner.clean(text)

            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(cleaned, encoding="utf-8")

            logger.info(f"Saved    : {output_file.name}")

        except Exception as exc:
            self.cleaner.stats.failed += 1
            logger.exception(f"Failed : {input_file.name}")
            logger.exception(exc)

    def clean_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.txt",
    ):
        files = sorted(input_dir.glob(pattern))

        logger.info("=" * 60)
        logger.info("Resume Text Cleaning Started")
        logger.info("=" * 60)

        logger.info("Found %d text files", len(files))

        for index, file in enumerate(files, start=1):
            logger.info("[%d/%d] %s", index, len(files), file.name)

            self.clean_file(file, output_dir / file.name)

        logger.info("=" * 60)
        logger.info("Cleaning Finished")
        logger.info("=" * 60)

    def export_statistics(self):
        report = self.cleaner.stats.report()
        report_path = REPORT_DIR / "cleaning_statistics.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        logger.info("Statistics saved : %s", report_path)

        return report_path


def main():
    cleaner = ResumeCleaner()
    cleaner.clean_directory(INPUT_DIR, OUTPUT_DIR)

    report = cleaner.export_statistics()
    stats = cleaner.cleaner.stats

    print("\n" + "=" * 70)
    print("TEXT CLEANING SUMMARY")
    print("=" * 70)

    print(f"Documents Processed        : {stats.documents}")
    print(f"Successful                : {stats.successful}")
    print(f"Failed                    : {stats.failed}")

    print()

    print(f"Characters Before         : {stats.original_characters}")
    print(f"Characters After          : {stats.cleaned_characters}")

    if stats.original_characters:
        ratio = (stats.cleaned_characters / stats.original_characters) * 100
        print(f"Text Preserved            : {ratio:.2f}%")

    print()

    print(f"Unicode Replacements      : {stats.unicode_replacements}")
    print(f"Hyphen Fixes              : {stats.hyphen_fixes}")
    print(f"Control Characters Removed: {stats.control_characters_removed}")
    print(f"Bullet Symbols Normalized : {stats.bullet_normalized}")
    print(f"Spaces Removed            : {stats.spaces_removed}")
    print(f"Blank Lines Reduced       : {stats.blank_lines_removed}")

    print()

    print(f"Cleaned Text Folder")
    print(f"   {OUTPUT_DIR}")

    print()

    print(f"Statistics")
    print(f"   {report}")

    print("=" * 70)


if __name__ == "__main__":
    main()
