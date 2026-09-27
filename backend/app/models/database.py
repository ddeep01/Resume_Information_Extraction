import sqlite3
from pathlib import Path

def get_db_connection(db_path: Path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not db_path.exists()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    if is_new:
        conn.close()
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
    return conn

def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        job_title TEXT NOT NULL,
        job_description TEXT,
        required_degree TEXT NOT NULL,
        required_specialization TEXT NOT NULL,
        minimum_experience REAL NOT NULL,
        minimum_publications INTEGER NOT NULL,
        publication_window_years INTEGER NOT NULL,
        top_n INTEGER NOT NULL,
        scoring_weights TEXT NOT NULL,
        processing_status TEXT NOT NULL,
        current_stage TEXT,
        total_candidates INTEGER DEFAULT 0,
        processed_candidates INTEGER DEFAULT 0,
        failed_candidates INTEGER DEFAULT 0,
        shortlisted_candidates INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT
    )
    """)

    # 2. Candidates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        candidate_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        source_file TEXT NOT NULL,
        full_name TEXT,
        current_designation TEXT,
        email TEXT,
        phone TEXT,
        education_json TEXT NOT NULL,
        publications_json TEXT NOT NULL,
        experience_json TEXT NOT NULL,
        shortlisting_json TEXT NOT NULL,
        eligible INTEGER DEFAULT 0,
        shortlisted INTEGER DEFAULT 0,
        final_score REAL DEFAULT 0.0,
        rank INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """)

    # 3. Institution Cache Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS institution_cache (
        institution_name TEXT PRIMARY KEY,
        tier TEXT NOT NULL,
        score REAL NOT NULL,
        reason TEXT,
        updated_at TEXT NOT NULL
    )
    """)

    # 4. Publication Venue Cache Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS publication_venue_cache (
        venue_name TEXT PRIMARY KEY,
        tier TEXT NOT NULL,
        score REAL NOT NULL,
        reason TEXT,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
