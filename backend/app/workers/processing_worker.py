import sys
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
from backend.app.services.results_exporter import ResultsExporter

logger = logging.getLogger("ProcessingWorker")

def log_step(msg: str):
    logger.info(msg)
    print(f"[RECRUITER-WORKER] {msg}", flush=True)

def run_session_processing(session_id: str):
    """
    Background worker thread function to process a recruitment session batch.
    Prints detailed step-by-step logs to terminal.
    """
    session_service = SessionService()
    candidate_service = CandidateService()
    orchestrator = ExtractionOrchestrator()
    llm_extractor = LLMExtractor()
    inst_classifier = InstitutionClassifier()
    pub_classifier = PublicationClassifier()

    session = session_service.get_session(session_id)
    if not session:
        log_step(f"ERROR: Session {session_id} not found for processing worker.")
        return

    log_step("=" * 70)
    log_step(f"STARTING SESSION PROCESSING: {session_id}")
    log_step(f"Job Title: '{session.job_title}' | Required: {session.required_degree} in {session.required_specialization}")
    log_step(f"Min Experience: {session.minimum_experience} yrs | Min Pubs: {session.minimum_publications} (Window: {session.publication_window_years} yrs) | Top N: {session.top_n}")
    log_step("=" * 70)

    session_dir = settings.SESSIONS_DIR / session_id
    uploaded_dir = session_dir / "uploaded"
    zip_files = list(uploaded_dir.glob("*.zip"))

    if not zip_files:
        log_step(f"ERROR: No zip file found in {uploaded_dir}")
        session_service.update_session_status(session_id, "FAILED", "NO_ZIP_FOUND")
        return

    zip_path = zip_files[0]

    try:
        # Stage 1: ZIP EXTRACTION
        log_step(f"--> [STAGE 1/8] Extracting ZIP Archive: {zip_path.name}")
        session_service.update_session_status(session_id, "PROCESSING", "ZIP_EXTRACTION")
        extracted_dir = session_dir / "extracted"
        candidates_with_files = ZipService.extract_zip_safely(zip_path, extracted_dir)
        
        total_files = len(candidates_with_files)
        log_step(f"    Discovered {total_files} candidate resume file(s).")

        if total_files == 0:
            log_step("ERROR: No valid PDF, DOCX, or TXT resume files discovered inside ZIP archive.")
            session_service.update_session_status(session_id, "FAILED", "NO_RESUMES_FOUND", total=0)
            return

        session_service.update_session_status(session_id, "PROCESSING", "TEXT_EXTRACTION", total=total_files, processed=0, failed=0)

        processed_count = 0
        failed_count = 0
        candidate_results = []

        # Process each discovered resume file
        for cand_id, file_path in candidates_with_files:
            log_step("-" * 70)
            log_step(f"--> Processing Candidate {cand_id} ({file_path.name}) [{processed_count+1}/{total_files}]")
            try:
                # Stage 2: TEXT EXTRACTION & CLEANING
                session_service.update_session_status(session_id, "PROCESSING", "TEXT_EXTRACTION", processed=processed_count, failed=failed_count)
                raw_text, cleaned_text, method = orchestrator.process_file(file_path)

                log_step(f"    [Step 1/6] Text Extraction ({method}): Raw = {len(raw_text)} chars, Cleaned = {len(cleaned_text)} chars")

                # Save raw & cleaned text
                (session_dir / "raw_text").mkdir(parents=True, exist_ok=True)
                (session_dir / "cleaned_text").mkdir(parents=True, exist_ok=True)
                (session_dir / "raw_text" / f"{cand_id}.txt").write_text(raw_text, encoding="utf-8")
                (session_dir / "cleaned_text" / f"{cand_id}.txt").write_text(cleaned_text, encoding="utf-8")

                if not cleaned_text:
                    log_step(f"    WARNING: Cleaned text empty for candidate file {file_path.name}. Skipping.")
                    failed_count += 1
                    continue

                # Stage 3: LLM STRUCTURED EXTRACTION
                session_service.update_session_status(session_id, "PROCESSING", "LLM_EXTRACTION", processed=processed_count, failed=failed_count)
                log_step(f"    [Step 2/6] LLM / Heuristic Structured JSON Extraction...")
                raw_extracted = llm_extractor.extract_candidate_data(cleaned_text, candidate_id=cand_id)

                p_info = raw_extracted.get("personal_information", {})
                cand_name = p_info.get("full_name") or "Unknown Candidate"
                cand_email = p_info.get("email") or "N/A"
                cand_desig = p_info.get("current_designation") or "N/A"
                log_step(f"        Extracted Profile: Name = '{cand_name}', Email = '{cand_email}', Role = '{cand_desig}'")

                # Stage 4: INSTITUTION CLASSIFICATION
                session_service.update_session_status(session_id, "PROCESSING", "INSTITUTION_CLASSIFIER", processed=processed_count, failed=failed_count)
                education_raw = raw_extracted.get("education", [])
                exp_raw = raw_extracted.get("experience", {})
                acad_exp_raw = exp_raw.get("academic", []) if isinstance(exp_raw, dict) else []
                ind_exp_raw = exp_raw.get("industry", []) if isinstance(exp_raw, dict) else []

                inst_names = [edu.get("university") or edu.get("institution") or "" for edu in education_raw]
                inst_names += [a_exp.get("institution") or "" for a_exp in acad_exp_raw]
                inst_names = [i for i in inst_names if i and i.strip()]
                
                batch_classified_insts = inst_classifier.classify_batch(inst_names) if inst_names else {}

                education_classified = []
                for edu in education_raw:
                    inst_name = (edu.get("university") or edu.get("institution") or "").strip()
                    class_res = batch_classified_insts.get(inst_name) or inst_classifier.classify(inst_name)
                    edu["institution_tier"] = class_res["tier"]
                    edu["institution_score"] = class_res["score"]
                    education_classified.append(edu)
                    log_step(f"        Education Tier: {edu.get('degree')} at '{inst_name}' -> {class_res['tier']} (Score: {class_res['score']})")

                acad_classified = []
                for a_exp in acad_exp_raw:
                    inst_name = (a_exp.get("institution") or "").strip()
                    class_res = batch_classified_insts.get(inst_name) or inst_classifier.classify(inst_name)
                    a_exp["institution_tier"] = class_res["tier"]
                    a_exp["institution_score"] = class_res["score"]
                    acad_classified.append(a_exp)
                    log_step(f"        Academic Exp Tier: '{inst_name}' ({a_exp.get('duration_years')} yrs) -> {class_res['tier']}")

                # Stage 5: PUBLICATION CLASSIFICATION
                session_service.update_session_status(session_id, "PROCESSING", "PUBLICATION_CLASSIFIER", processed=processed_count, failed=failed_count)
                pubs_raw = raw_extracted.get("publications", [])
                venue_names = [(pub.get("venue_name") or pub.get("publisher") or "").strip() for pub in pubs_raw]
                venue_names = [v for v in venue_names if v]

                batch_classified_pubs = pub_classifier.classify_batch(venue_names) if venue_names else {}

                pubs_classified = []
                for pub in pubs_raw:
                    venue = (pub.get("venue_name") or pub.get("publisher") or "").strip()
                    v_res = batch_classified_pubs.get(venue) or pub_classifier.classify(venue)
                    pub["venue_tier"] = v_res["tier"]
                    pub["venue_score"] = v_res["score"]
                    pubs_classified.append(pub)

                log_step(f"        Publications Count: {len(pubs_classified)}")

                candidate_dict = {
                    "candidate_id": cand_id,
                    "source_file": file_path.name,
                    "personal_information": p_info,
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
                candidate_dict["publications"] = window_pubs

                log_step(f"    [Step 3/6] Eligibility: Eligible = {is_eligible} (Total Exp: {total_exp:.1f} yrs, Window Pubs: {len(window_pubs)})")
                if reasons:
                    log_step(f"        Evaluation Flags: {', '.join(reasons)}")

                # Stage 7: SCORING
                session_service.update_session_status(session_id, "PROCESSING", "SCORING", processed=processed_count, failed=failed_count)
                edu_score = calculate_education_score(education_classified)
                pub_score = calculate_publication_score(window_pubs, target_min_pubs=session.minimum_publications)
                acad_score = calculate_academic_experience_score(acad_classified)
                ind_score = calculate_industry_experience_score(ind_exp_raw)

                weights = session.scoring_weights.model_dump()
                final_score = calculate_final_score(edu_score, pub_score, acad_score, ind_score, weights)

                log_step(f"    [Step 4/6] Component Scores: Edu={edu_score*100:.1f}, Pub={pub_score*100:.1f}, AcadExp={acad_score*100:.1f}, IndExp={ind_score*100:.1f}")
                log_step(f"        ==> FINAL WEIGHTED SCORE: {final_score:.2f} / 100")

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
                log_step(f"ERROR processing candidate {cand_id} ({file_path.name}): {e}")
                logger.error(f"Error processing candidate {cand_id} ({file_path.name}): {e}", exc_info=True)
                failed_count += 1
                # Save failed candidate record for human faculty review & intervention
                failed_dir = session_dir / "failed_candidates"
                failed_dir.mkdir(parents=True, exist_ok=True)
                raw_txt_file = session_dir / "raw_text" / f"{cand_id}.txt"
                raw_txt = raw_txt_file.read_text(encoding="utf-8") if raw_txt_file.exists() else "Raw text unavailable"
                failed_data = {
                    "candidate_id": cand_id,
                    "filename": file_path.name,
                    "error": str(e),
                    "raw_text": raw_txt
                }
                (failed_dir / f"{cand_id}.json").write_text(json.dumps(failed_data, indent=2), encoding="utf-8")

        # Stage 8: RANKING AND SHORTLISTING
        log_step("-" * 70)
        log_step(f"--> [STAGE 8/8] Sorting {len(candidate_results)} candidates & Selecting Top-{session.top_n} Shortlist...")
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

        # Export session results to project root `results/<session_id>/`
        try:
            ResultsExporter.export_session_results(session.model_dump(), final_candidates)
            log_step(f"--> Exported full session results to results/{session_id}/")
        except Exception as ex_err:
            logger.warning(f"Failed to export results to root results folder: {ex_err}")

        # Stage 9: COMPLETED
        session_service.update_session_status(
            session_id=session_id,
            status="COMPLETED",
            stage="COMPLETED",
            processed=processed_count,
            failed=failed_count,
            shortlisted=shortlisted_count
        )

        log_step("=" * 70)
        log_step(f"SESSION {session_id} COMPLETED SUCCESSFULLY!")
        log_step(f"Processed: {processed_count} | Shortlisted: {shortlisted_count} | Failed: {failed_count}")
        log_step(f"TOP SHORTLISTED CANDIDATES:")
        for cand in final_candidates:
            if cand["shortlisting"]["shortlisted"]:
                r = cand["shortlisting"]["rank"]
                nm = cand["personal_information"].get("full_name")
                sc = cand["shortlisting"]["final_score"]
                log_step(f"   Rank #{r}: {nm} | Final Score: {sc:.2f}")
        log_step("=" * 70)

    except Exception as e:
        log_step(f"FATAL WORKER ERROR for session {session_id}: {e}")
        logger.error(f"Fatal worker failure for session {session_id}: {e}", exc_info=True)
        session_service.update_session_status(session_id, "FAILED", "FATAL_ERROR")

def start_background_processing(session_id: str):
    t = threading.Thread(target=run_session_processing, args=(session_id,), daemon=True)
    t.start()
    return t
