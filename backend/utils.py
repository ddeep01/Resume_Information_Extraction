from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_RESUME_DIR = BASE_DIR / "data" / "raw_resumes"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted_text"
CLEANED_DIR = BASE_DIR / "data" / "cleaned_text"



def ensure_directories():
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)