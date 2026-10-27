import pytest
from pathlib import Path
from backend.app.config import settings
from backend.app.models.database import init_db

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_app_data")
    orig_db = settings.DB_PATH
    orig_sessions = settings.SESSIONS_DIR
    orig_results = settings.RESULTS_DIR
    orig_cache = settings.CACHE_DIR

    settings.DATA_DIR = temp_dir
    settings.DB_PATH = temp_dir / "test_app.db"
    settings.SESSIONS_DIR = temp_dir / "sessions"
    settings.RESULTS_DIR = temp_dir / "results"
    settings.CACHE_DIR = temp_dir / "cache"

    settings.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    init_db(settings.DB_PATH)

    yield

    settings.DB_PATH = orig_db
    settings.SESSIONS_DIR = orig_sessions
    settings.RESULTS_DIR = orig_results
    settings.CACHE_DIR = orig_cache
