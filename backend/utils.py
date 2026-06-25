from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_RESUME_DIR = BASE_DIR / "data" / "raw_resumes"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted_text"
CLEANED_DIR = BASE_DIR / "data" / "cleaned_text"

FILE_HASH_CSV = BASE_DIR / "data" / "metadata" / "file_hashes.csv"
TEXT_HASH_CSV = BASE_DIR / "data" / "metadata" / "text_hashes.csv"


def ensure_directories():
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)