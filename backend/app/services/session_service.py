import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.app.config import settings
from backend.app.models.database import get_db_connection, init_db
from backend.app.schemas.recruiter import CreateSessionRequest, SessionResponse, ScoringWeights

logger = logging.getLogger("SessionService")

class SessionService:
    def __init__(self):
        init_db(settings.DB_PATH)

    def generate_session_id(self) -> str:
        year = datetime.now().year
        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0] + 1
        conn.close()
        return f"SES-{year}-{count:04d}"

    def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        session_id = self.generate_session_id()
        created_at = datetime.now().isoformat()
        weights_dict = request.scoring_weights.model_dump() if request.scoring_weights else ScoringWeights().model_dump()

        # Create session directory structure
        session_dir = settings.SESSIONS_DIR / session_id
        for sub in ["uploaded", "extracted", "raw_text", "cleaned_text", "candidates", "results"]:
            (session_dir / sub).mkdir(parents=True, exist_ok=True)

        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO sessions (
            session_id, job_title, job_description, required_degree, required_specialization,
            minimum_experience, minimum_publications, publication_window_years, top_n,
            scoring_weights, processing_status, current_stage, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, request.job_title, request.job_description or "", request.required_degree,
            request.required_specialization, request.minimum_experience, request.minimum_publications,
            request.publication_window_years, request.top_n, json.dumps(weights_dict),
            "CREATED", "INITIAL", created_at
        ))
        conn.commit()
        conn.close()

        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[SessionResponse]:
        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        weights = ScoringWeights(**json.loads(row["scoring_weights"]))
        return SessionResponse(
            session_id=row["session_id"],
            job_title=row["job_title"],
            job_description=row["job_description"],
            required_degree=row["required_degree"],
            required_specialization=row["required_specialization"],
            minimum_experience=row["minimum_experience"],
            minimum_publications=row["minimum_publications"],
            publication_window_years=row["publication_window_years"],
            top_n=row["top_n"],
            scoring_weights=weights,
            processing_status=row["processing_status"],
            current_stage=row["current_stage"] or "INITIAL",
            total_candidates=row["total_candidates"],
            processed_candidates=row["processed_candidates"],
            failed_candidates=row["failed_candidates"],
            shortlisted_candidates=row["shortlisted_candidates"],
            created_at=row["created_at"],
            completed_at=row["completed_at"]
        )

    def list_sessions(self) -> List[SessionResponse]:
        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for r in rows:
            s = self.get_session(r["session_id"])
            if s:
                sessions.append(s)
        return sessions

    def update_session_status(self, session_id: str, status: str, stage: str, processed: int = None, failed: int = None, total: int = None, shortlisted: int = None):
        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        
        updates = ["processing_status=?", "current_stage=?"]
        params = [status, stage]
        
        if processed is not None:
            updates.append("processed_candidates=?")
            params.append(processed)
        if failed is not None:
            updates.append("failed_candidates=?")
            params.append(failed)
        if total is not None:
            updates.append("total_candidates=?")
            params.append(total)
        if shortlisted is not None:
            updates.append("shortlisted_candidates=?")
            params.append(shortlisted)
        if status in ["COMPLETED", "FAILED"]:
            updates.append("completed_at=?")
            params.append(datetime.now().isoformat())

        params.append(session_id)
        sql = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id=?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
