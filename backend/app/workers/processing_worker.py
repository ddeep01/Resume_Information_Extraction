import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List

from backend.app.config import settings
from backend.app.services.session_service import SessionService
from backend.app.services.candidate_service import CandidateService
from backend.app.services.zip_service import ZipService
from backend.app.pipeline.orchestrator import ExtractionOrchestrator
from backend.app.llm.extraction import LLMExtractor
from backend.app.classification.institution_classifier import InstitutionClassifier
from backend.app.classification.publication_classifier import PublicationClassifier
from backend.app.shortlisting.eligibility import evaluate_candidate_eligibility
from backend.app.shortlisting.scoring import (
    calculate_education_score,
    calculate_publication_score,
    calculate_academic_experience_score,
    calculate_industry_experience_score,
    calculate_final_score
)
from backend.app.shortlisting.ranking import rank_and_shortlist_candidates

logger = logging.getLogger("ProcessingWorker")

def run_session_processing(session_id: str):
    """
    Background worker thread function to process a recruitment session batch.
    """
    session_service = SessionService()
    candidate_service = CandidateService()
    orchestrator = ExtractionOrchestrator()
    llm_extractor = LLMExtractor()
    inst_classifier = InstitutionClassifier()
    pub_classifier = PublicationClassifier()

    session = session_service.get_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found for processing worker.")
        return

    session_dir = settings.SESSIONS_DIR / session_id
    uploaded_dir = session_dir / "uploaded"
    zip_files = list(uploaded_dir.glob("*.zip"))

    if not zip_files:
        logger.error(f"No zip file found in {uploaded_dir}")
        session_service.update_session_status(session_id, "FAILED", "NO_ZIP_FOUND")
        return

    zip_path = zip_files[0]

    try:
        # Stage 1: ZIP EXTRACTION
        session_service.update_session_status(session_id, "PROCESSING", "ZIP_EXTRACTION")
        extracted_dir = session_dir / "extracted"
        candidates_with_files = ZipService.extract_zip_safely(zip_path, extracted_dir)
        
        total_files = len(candidates_with_files)
        if total_files == 0:
            session_service.update_session_status(session_id, "FAILED", "NO_RESUMES_FOUND", total=0)
            return

        session_service.update_session_status(session_id, "PROCESSING", "TEXT_EXTRACTION", total=total_files, processed=0, failed=0)

        processed_count = 0
        failed_count = 0
        candidate_results = []

        # Process each discovered resume file
        for cand_id, file_path in candidates_with_files:
            try:
                # Stage 2: TEXT EXTRACTION & CLEANING
                session_service.update_session_status(session_id, "PROCESSING", "TEXT_EXTRACTION", processed=processed_count, failed=failed_count)
                raw_text, cleaned_text, method = orchestrator.process_file(file_path)

                # Save raw & cleaned text
                (session_dir / "raw_text" / f"{cand_id}.txt").write_text(raw_text, encoding="utf-8")
                (session_dir / "cleaned_text" / f"{cand_id}.txt").write_text(cleaned_text, encoding="utf-8")

                if not cleaned_text:
                    logger.warning(f"Extracted text empty for {file_path.name}")
                    failed_count += 1
                    continue

                # Stage 3: LLM STRUCTURED EXTRACTION
                session_service.update_session_status(session_id, "PROCESSING", "LLM_EXTRACTION", processed=processed_count, failed=failed_count)
                raw_extracted = llm_extractor.extract_candidate_data(cleaned_text)

                # Stage 4: INSTITUTION CLASSIFICATION
                session_service.update_session_status(session_id, "PROCESSING", "INSTITUTION_CLASSIFIER", processed=processed_count, failed=failed_count)
                education_raw = raw_extracted.get("education", [])
                education_classified = []
                for edu in education_raw:
                    inst_name = edu.get("university") or edu.get("institution") or ""
                    class_res = inst_classifier.classify(inst_name)
                    edu["institution_tier"] = class_res["tier"]
                    edu["institution_score"] = class_res["score"]
                    education_classified.append(edu)

                exp_raw = raw_extracted.get("experience", {})
                acad_exp_raw = exp_raw.get("academic", []) if isinstance(exp_raw, dict) else []
                ind_exp_raw = exp_raw.get("industry", []) if isinstance(exp_raw, dict) else []

                acad_classified = []
                for a_exp in acad_exp_raw:
                    inst_name = a_exp.get("institution") or ""
                    class_res = inst_classifier.classify(inst_name)
                    a_exp["institution_tier"] = class_res["tier"]
                    a_exp["institution_score"] = class_res["score"]
                    acad_classified.append(a_exp)

                # Stage 5: PUBLICATION CLASSIFICATION
                session_service.update_session_status(session_id, "PROCESSING", "PUBLICATION_CLASSIFIER", processed=processed_count, failed=failed_count)
                pubs_raw = raw_extracted.get("publications", [])
                pubs_classified = []
                for pub in pubs_raw:
                    venue = pub.get("venue_name") or pub.get("publisher") or ""
                    v_res = pub_classifier.classify(venue)
                    pub["venue_tier"] = v_res["tier"]
                    pub["venue_score"] = v_res["score"]
                    pubs_classified.append(pub)

                candidate_dict = {
                    "candidate_id": cand_id,
                    "source_file": file_path.name,
                    "personal_information": raw_extracted.get("personal_information", {}),
                    "education": education_classified,
                    "publications": pubs_classified,
                    "experience": {
                        "academic": acad_classified,
                        "industry": ind_exp_raw
                    }
                }

                # Stage 6: ELIGIBILITY EVALUATION
                session_service.update_session_status(session_id, "PROCESSING", "ELIGIBILITY_FILTERING", processed=processed_count, failed=failed_count)
                is_eligible, reasons, window_pubs, total_exp = evaluate_candidate_eligibility(
                    candidate_dict,
                    required_degree=session.required_degree,
                    required_specialization=session.required_specialization,
                    minimum_experience=session.minimum_experience,
                    minimum_publications=session.minimum_publications,
                    publication_window_years=session.publication_window_years
                )

                # Update publications list with window flags
                candidate_dict["publications"] = window_pubs

                # Stage 7: SCORING
                session_service.update_session_status(session_id, "PROCESSING", "SCORING", processed=processed_count, failed=failed_count)
                edu_score = calculate_education_score(education_classified)
                pub_score = calculate_publication_score(window_pubs, target_min_pubs=session.minimum_publications)
                acad_score = calculate_academic_experience_score(acad_classified)
                ind_score = calculate_industry_experience_score(ind_exp_raw)

                weights = session.scoring_weights.model_dump()
                final_score = calculate_final_score(edu_score, pub_score, acad_score, ind_score, weights)

                candidate_dict["shortlisting"] = {
                    "eligible": is_eligible,
                    "shortlisted": False,
                    "education_score": edu_score,
                    "publication_score": pub_score,
                    "academic_experience_score": acad_score,
                    "industry_experience_score": ind_score,
                    "final_score": final_score,
                    "rank": None,
                    "reasons": reasons
                }

                candidate_results.append(candidate_dict)
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing candidate {cand_id} ({file_path.name}): {e}", exc_info=True)
                failed_count += 1

        # Stage 8: RANKING AND SHORTLISTING
        session_service.update_session_status(session_id, "PROCESSING", "RANKING", processed=processed_count, failed=failed_count)
        final_candidates = rank_and_shortlist_candidates(candidate_results, top_n=session.top_n)

        # Save all candidate JSONs and database entries
        shortlisted_count = 0
        for cand in final_candidates:
            if cand["shortlisting"]["shortlisted"]:
                shortlisted_count += 1
            candidate_service.save_candidate(session_id, cand)

        # Write summary JSON files to session results directory
        results_dir = session_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "all_candidates.json").write_text(json.dumps(final_candidates, indent=2), encoding="utf-8")
        shortlisted_list = [c for c in final_candidates if c["shortlisting"]["shortlisted"]]
        (results_dir / "shortlist.json").write_text(json.dumps(shortlisted_list, indent=2), encoding="utf-8")

        # Stage 9: COMPLETED
        session_service.update_session_status(
            session_id=session_id,
            status="COMPLETED",
            stage="COMPLETED",
            processed=processed_count,
            failed=failed_count,
            shortlisted=shortlisted_count
        )
        logger.info(f"Session {session_id} completed successfully. Processed: {processed_count}, Shortlisted: {shortlisted_count}")

    except Exception as e:
        logger.error(f"Fatal worker failure for session {session_id}: {e}", exc_info=True)
        session_service.update_session_status(session_id, "FAILED", "FATAL_ERROR")

def start_background_processing(session_id: str):
    t = threading.Thread(target=run_session_processing, args=(session_id,), daemon=True)
    t.start()
    return t
