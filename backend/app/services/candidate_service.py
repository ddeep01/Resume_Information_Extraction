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
        try:
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
        finally:
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
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates WHERE session_id=? AND candidate_id=?", (session_id, candidate_id))
            row = cursor.fetchone()
        finally:
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

        # Fallback 1: Query SQLite database if no JSON files in cand_dir
        if not candidates:
            conn = get_db_connection(settings.DB_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM candidates WHERE session_id=?", (session_id,))
                rows = cursor.fetchall()
                for row in rows:
                    try:
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
                        candidates.append(CandidateSchema(**data))
                    except Exception as e:
                        logger.warning(f"Error loading candidate from DB row: {e}")
            finally:
                conn.close()

        # Fallback 2: Check results directory
        if not candidates:
            candidates = self.load_candidates_from_results(session_id)
            for c in candidates:
                try:
                    self.save_candidate(session_id, c.model_dump())
                except Exception as e:
                    logger.warning(f"Error caching loaded candidate {c.candidate_id}: {e}")

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

    def load_candidates_from_results(self, session_id: str) -> List[CandidateSchema]:
        res_dir = settings.RESULTS_DIR / session_id
        if not res_dir.exists():
            return []

        llm_file = res_dir / "llm_extracted_outputs.json"
        sl_file = res_dir / "shortlisting_and_top2_result.json"
        pub_file = res_dir / "publication_classifications.json"
        exp_file = res_dir / "experience_classifications.json"

        if not (llm_file.exists() and sl_file.exists()):
            return []

        try:
            with open(llm_file, "r", encoding="utf-8") as f:
                llm_data = json.load(f)
            with open(sl_file, "r", encoding="utf-8") as f:
                sl_data = json.load(f)
            pub_data = {}
            if pub_file.exists():
                with open(pub_file, "r", encoding="utf-8") as f:
                    pub_data = json.load(f)
            exp_data = {}
            if exp_file.exists():
                with open(exp_file, "r", encoding="utf-8") as f:
                    exp_data = json.load(f)

            sl_map = {c["candidate_id"]: c for c in sl_data.get("all_evaluated_candidates", [])}
            top_map = {c["candidate_id"]: c for c in sl_data.get("top_shortlisted_candidates", [])}
            pub_map = {c["candidate_id"]: c for c in pub_data.get("publication_classifications_by_candidate", [])}
            exp_map = {c["candidate_id"]: c for c in exp_data.get("experience_classifications_by_candidate", [])}

            candidates = []
            for raw in llm_data.get("candidates_llm_extracted_data", []):
                cid = raw.get("candidate_id")
                sl_info = sl_map.get(cid, {})
                top_info = top_map.get(cid, {})
                pub_info = pub_map.get(cid, {})
                exp_info = exp_map.get(cid, {})

                comp_scores = top_info.get("component_scores", {})
                edu_score = comp_scores.get("education_score", 0.0)
                pub_score = comp_scores.get("publication_score", pub_info.get("publication_score", 0.0))
                acad_score = comp_scores.get("academic_experience_score", exp_info.get("academic_experience_score", 0.0))
                ind_score = comp_scores.get("industry_experience_score", exp_info.get("industry_experience_score", 0.0))

                exp_dict = raw.get("extracted_experience", {})
                if not isinstance(exp_dict, dict):
                    exp_dict = {"academic": [], "industry": []}

                cand_dict = {
                    "candidate_id": cid,
                    "source_file": raw.get("source_file") or f"{cid}.pdf",
                    "personal_information": {
                        "full_name": raw.get("candidate_name"),
                        "current_designation": raw.get("current_designation"),
                        "email": raw.get("email"),
                        "phone": raw.get("phone")
                    },
                    "education": raw.get("extracted_education", []),
                    "publications": raw.get("extracted_publications", []),
                    "experience": exp_dict,
                    "shortlisting": {
                        "eligible": sl_info.get("eligible", False),
                        "shortlisted": sl_info.get("shortlisted", False),
                        "education_score": edu_score,
                        "publication_score": pub_score,
                        "academic_experience_score": acad_score,
                        "industry_experience_score": ind_score,
                        "final_score": sl_info.get("final_score", 0.0),
                        "rank": sl_info.get("rank"),
                        "reasons": sl_info.get("reasons", [])
                    }
                }
                candidates.append(CandidateSchema(**cand_dict))
            return candidates
        except Exception as e:
            logger.error(f"Error loading candidates from results for session {session_id}: {e}")
            return []

    def get_failed_candidates(self, session_id: str) -> List[Dict[str, Any]]:
        failed_dir = settings.SESSIONS_DIR / session_id / "failed_candidates"
        failed_list = []
        if failed_dir.exists():
            for f in failed_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        failed_list.append(json.load(file))
                except Exception as e:
                    logger.warning(f"Error reading failed candidate file {f}: {e}")
        return failed_list

