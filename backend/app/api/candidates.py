from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.candidate import CandidateSchema
from backend.app.schemas.results import CandidateListResponse
from backend.app.services.candidate_service import CandidateService
from backend.app.services.session_service import SessionService

router = APIRouter(prefix="/sessions/{session_id}", tags=["Candidates"])
candidate_service = CandidateService()
session_service = SessionService()

@router.get("/candidates", response_model=CandidateListResponse)
def list_candidates(
    session_id: str,
    search: Optional[str] = Query(None, description="Search candidate name, email, or designation"),
    status: Optional[str] = Query(None, description="Filter: shortlisted | eligible | ineligible"),
    sort_by: Optional[str] = Query("final_score", description="Sort: final_score | rank | name")
):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    candidates = candidate_service.get_session_candidates(session_id, search=search, status_filter=status, sort_by=sort_by)
    eligible_count = sum(1 for c in candidates if c.shortlisting.eligible)
    shortlisted_count = sum(1 for c in candidates if c.shortlisting.shortlisted)

    return CandidateListResponse(
        session_id=session_id,
        total=len(candidates),
        eligible_count=eligible_count,
        shortlisted_count=shortlisted_count,
        candidates=candidates
    )

@router.get("/shortlist", response_model=CandidateListResponse)
def get_shortlist(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    candidates = candidate_service.get_session_candidates(session_id, status_filter="shortlisted", sort_by="rank")
    return CandidateListResponse(
        session_id=session_id,
        total=len(candidates),
        eligible_count=len(candidates),
        shortlisted_count=len(candidates),
        candidates=candidates
    )

@router.get("/candidates/{candidate_id}", response_model=CandidateSchema)
def get_candidate_detail(session_id: str, candidate_id: str):
    candidate = candidate_service.get_candidate(session_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.get("/failed_candidates")
def get_failed_candidates(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    failed_list = candidate_service.get_failed_candidates(session_id)
    return {
        "session_id": session_id,
        "failed_count": len(failed_list),
        "failed_candidates": failed_list
    }

