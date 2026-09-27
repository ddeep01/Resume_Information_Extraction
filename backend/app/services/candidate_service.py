import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.app.config import settings
from backend.app.models.database import get_db_connection
from backend.app.schemas.candidate import CandidateSchema

logger = logging.getLogger("CandidateService")

class CandidateService:
    def save_candidate(self, session_id: str, candidate_data: Dict[str, Any]):
        cand_id = candidate_data["candidate_id"]
        source_file = candidate_data.get("source_file", "")
        personal = candidate_data.get("personal_information", {})
        full_name = personal.get("full_name")
        current_desig = personal.get("current_designation")
        email = personal.get("email")
        phone = personal.get("phone")

        shortlisting = candidate_data.get("shortlisting", {})
        eligible = 1 if shortlisting.get("eligible") else 0
        shortlisted = 1 if shortlisting.get("shortlisted") else 0
        final_score = float(shortlisting.get("final_score") or 0.0)
        rank = shortlisting.get("rank")

        # Save JSON to session directory
        cand_dir = settings.SESSIONS_DIR / session_id / "candidates"
        cand_dir.mkdir(parents=True, exist_ok=True)
        file_path = cand_dir / f"{cand_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(candidate_data, f, indent=2)

        # Upsert into SQLite
        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO candidates (
            candidate_id, session_id, source_file, full_name, current_designation,
            email, phone, education_json, publications_json, experience_json,
            shortlisting_json, eligible, shortlisted, final_score, rank, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cand_id, session_id, source_file, full_name, current_desig, email, phone,
            json.dumps(candidate_data.get("education", [])),
            json.dumps(candidate_data.get("publications", [])),
            json.dumps(candidate_data.get("experience", {})),
            json.dumps(shortlisting),
            eligible, shortlisted, final_score, rank, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_candidate(self, session_id: str, candidate_id: str) -> Optional[CandidateSchema]:
        file_path = settings.SESSIONS_DIR / session_id / "candidates" / f"{candidate_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return CandidateSchema(**data)
            except Exception as e:
                logger.error(f"Error reading candidate JSON {file_path}: {e}")

        conn = get_db_connection(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE session_id=? AND candidate_id=?", (session_id, candidate_id))
        row = cursor.fetchone()
        conn.close()

        if row:
            data = {
                "candidate_id": row["candidate_id"],
                "source_file": row["source_file"],
                "personal_information": {
                    "full_name": row["full_name"],
                    "current_designation": row["current_designation"],
                    "email": row["email"],
                    "phone": row["phone"]
                },
                "education": json.loads(row["education_json"]),
                "publications": json.loads(row["publications_json"]),
                "experience": json.loads(row["experience_json"]),
                "shortlisting": json.loads(row["shortlisting_json"])
            }
            return CandidateSchema(**data)
        return None

    def get_session_candidates(
        self,
        session_id: str,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,  # "shortlisted", "eligible", "ineligible"
        sort_by: Optional[str] = "final_score"
    ) -> List[CandidateSchema]:
        cand_dir = settings.SESSIONS_DIR / session_id / "candidates"
        candidates = []
        if cand_dir.exists():
            for f in cand_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        candidates.append(CandidateSchema(**data))
                except Exception as e:
                    logger.warning(f"Error loading {f}: {e}")

        # Search filter
        if search and search.strip():
            s = search.strip().lower()
            candidates = [
                c for c in candidates
                if (c.personal_information.full_name and s in c.personal_information.full_name.lower()) or
                   (c.personal_information.email and s in c.personal_information.email.lower()) or
                   (c.personal_information.current_designation and s in c.personal_information.current_designation.lower())
            ]

        # Status filter
        if status_filter:
            sf = status_filter.strip().lower()
            if sf == "shortlisted":
                candidates = [c for c in candidates if c.shortlisting.shortlisted]
            elif sf == "eligible":
                candidates = [c for c in candidates if c.shortlisting.eligible]
            elif sf == "ineligible":
                candidates = [c for c in candidates if not c.shortlisting.eligible]

        # Sort
        if sort_by == "final_score":
            candidates.sort(key=lambda c: c.shortlisting.final_score, reverse=True)
        elif sort_by == "rank":
            candidates.sort(key=lambda c: c.shortlisting.rank if c.shortlisting.rank is not None else 9999)
        elif sort_by == "name":
            candidates.sort(key=lambda c: c.personal_information.full_name or "")

        return candidates
