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
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions WHERE session_id LIKE ?", (f"SES-{year}-%",))
            rows = cursor.fetchall()
            existing_numbers = set()
            for r in rows:
                try:
                    num = int(r["session_id"].split("-")[-1])
                    existing_numbers.add(num)
                except (ValueError, IndexError):
                    pass
            next_num = max(existing_numbers, default=0) + 1
            while next_num in existing_numbers:
                next_num += 1
            return f"SES-{year}-{next_num:04d}"
        finally:
            conn.close()

    def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        session_id = self.generate_session_id()
        created_at = datetime.now().isoformat()
        weights_dict = request.scoring_weights.model_dump() if request.scoring_weights else ScoringWeights().model_dump()

        # Create session directory structure
        session_dir = settings.SESSIONS_DIR / session_id
        for sub in ["uploaded", "extracted", "raw_text", "cleaned_text", "candidates", "results"]:
            (session_dir / sub).mkdir(parents=True, exist_ok=True)

        conn = get_db_connection(settings.DB_PATH)
        try:
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
        finally:
            conn.close()

        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[SessionResponse]:
        conn = get_db_connection(settings.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,))
            row = cursor.fetchone()
        finally:
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

    def sync_sessions_from_results(self):
        """
        Scans settings.RESULTS_DIR for any session directories (e.g. SES-2026-0001).
        If the session is not registered in the database, automatically registers it
        and populates candidate records into SQLite and sessions cache.
        """
        results_dir = settings.RESULTS_DIR
        if not results_dir.exists():
            return

        conn = get_db_connection(settings.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions")
            existing_session_ids = {row["session_id"] for row in cursor.fetchall()}

            for s_dir in sorted(results_dir.glob("SES-*")):
                session_id = s_dir.name
                if session_id in existing_session_ids:
                    continue

                sl_file = s_dir / "shortlisting_and_top2_result.json"
                if not sl_file.exists():
                    continue

                try:
                    with open(sl_file, "r", encoding="utf-8") as f:
                        sl_data = json.load(f)

                    meta = sl_data.get("job_meta", {})
                    all_eval = sl_data.get("all_evaluated_candidates", [])
                    top_short = sl_data.get("top_shortlisted_candidates", [])

                    job_title = meta.get("job_title", "Faculty Position")
                    req_degree = meta.get("required_degree", "PhD")
                    req_spec = meta.get("required_specialization", "Computer Science")
                    min_exp = float(meta.get("minimum_experience_years", meta.get("minimum_experience", 3.0)))
                    min_pubs = int(meta.get("minimum_publications", 5))
                    pub_window = int(meta.get("publication_window_years", 5))
                    top_n = int(meta.get("top_n_requested", meta.get("top_n", 5)))

                    weights = meta.get("scoring_weights", {
                        "education": 0.35, "publication": 0.30, "academic_experience": 0.20, "industry_experience": 0.15
                    })

                    total_cand = len(all_eval)
                    shortlisted_cand = len(top_short)
                    failed_cand = 0
                    processed_cand = total_cand

                    mtime = datetime.fromtimestamp(sl_file.stat().st_mtime).isoformat()

                    cursor.execute("""
                    INSERT OR REPLACE INTO sessions (
                        session_id, job_title, job_description, required_degree, required_specialization,
                        minimum_experience, minimum_publications, publication_window_years, top_n,
                        scoring_weights, processing_status, current_stage, total_candidates,
                        processed_candidates, failed_candidates, shortlisted_candidates, created_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, job_title, "", req_degree, req_spec, min_exp, min_pubs, pub_window,
                        top_n, json.dumps(weights), "COMPLETED", "COMPLETED", total_cand, processed_cand,
                        failed_cand, shortlisted_cand, mtime, mtime
                    ))
                    conn.commit()
                    existing_session_ids.add(session_id)
                    logger.info(f"Auto-synced session {session_id} from results into database.")
                except Exception as err:
                    logger.error(f"Error syncing session {session_id} from results: {err}")
        finally:
            conn.close()

    def list_sessions(self) -> List[SessionResponse]:
        self.sync_sessions_from_results()
        conn = get_db_connection(settings.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions ORDER BY created_at DESC")
            rows = cursor.fetchall()
        finally:
            conn.close()

        sessions = []
        for r in rows:
            s = self.get_session(r["session_id"])
            if s:
                sessions.append(s)
        return sessions

    def update_session_status(self, session_id: str, status: str, stage: str, processed: int = None, failed: int = None, total: int = None, shortlisted: int = None):
        conn = get_db_connection(settings.DB_PATH)
        try:
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
        finally:
            conn.close()

    def clear_all_data(self) -> Dict[str, Any]:
        import shutil
        # Clear session directories
        if settings.SESSIONS_DIR.exists():
            for item in settings.SESSIONS_DIR.glob("*"):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

        # Clear results directories
        if settings.RESULTS_DIR.exists():
            for item in settings.RESULTS_DIR.glob("*"):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

        # Clear cache directory
        if settings.CACHE_DIR.exists():
            for item in settings.CACHE_DIR.glob("*"):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

        # Reset DB tables
        conn = get_db_connection(settings.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidates")
            cursor.execute("DELETE FROM sessions")
            conn.commit()
        finally:
            conn.close()

        logger.info("Cleared all session data, results, and database tables.")
        return {"status": "success", "message": "All session data, cache, and database entries cleared successfully."}

    def delete_session(self, session_id: str) -> bool:
        import shutil
        session_dir = settings.SESSIONS_DIR / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

        results_dir = settings.RESULTS_DIR / session_id
        if results_dir.exists():
            shutil.rmtree(results_dir, ignore_errors=True)

        conn = get_db_connection(settings.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidates WHERE session_id=?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            deleted_count = cursor.rowcount
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Deleted session {session_id} and associated candidate records.")
        return deleted_count > 0


