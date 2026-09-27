import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings:
    PROJECT_NAME: str = "Recruiter Resume Shortlisting & Ranking System"
    VERSION: str = "1.0.0"
    
    # Storage Directories
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    SESSIONS_DIR: Path = DATA_DIR / "sessions"
    CACHE_DIR: Path = DATA_DIR / "cache"
    TEST_RESUMES_DIR: Path = DATA_DIR / "test_resumes"
    DB_PATH: Path = DATA_DIR / "app.db"
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama") # ollama, openai, mock
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    
    # Tier Weights
    TIER_1_SCORE: float = 1.00
    TIER_2_SCORE: float = 0.66
    TIER_3_SCORE: float = 0.33
    
    def __init__(self):
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.TEST_RESUMES_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
