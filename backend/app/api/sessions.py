import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from backend.app.config import settings
from backend.app.schemas.recruiter import CreateSessionRequest, SessionResponse
from backend.app.schemas.results import ProcessingStatusResponse
from backend.app.services.session_service import SessionService
from backend.app.workers.processing_worker import start_background_processing

router = APIRouter(prefix="/sessions", tags=["Recruitment Sessions"])
session_service = SessionService()

@router.post("", response_model=SessionResponse, status_code=201)
def create_session(request: CreateSessionRequest):
    return session_service.create_session(request)

@router.get("", response_model=List[SessionResponse])
def list_sessions():
    return session_service.list_sessions()

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/upload", response_model=SessionResponse)
def upload_resumes(session_id: str, file: UploadFile = File(...)):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    session_dir = settings.SESSIONS_DIR / session_id / "uploaded"
    session_dir.mkdir(parents=True, exist_ok=True)
    target_zip = session_dir / "resumes.zip"

    with open(target_zip, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    session_service.update_session_status(session_id, "UPLOADED", "ZIP_UPLOADED")
    return session_service.get_session(session_id)

@router.post("/{session_id}/start", response_model=ProcessingStatusResponse)
def start_processing(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    uploaded_zip = settings.SESSIONS_DIR / session_id / "uploaded" / "resumes.zip"
    if not uploaded_zip.exists():
        raise HTTPException(status_code=400, detail="No uploaded resumes.zip file found for session")

    session_service.update_session_status(session_id, "PROCESSING", "STARTING")
    start_background_processing(session_id)

    return ProcessingStatusResponse(
        session_id=session_id,
        status="PROCESSING",
        stage="STARTING",
        total=session.total_candidates,
        processed=0,
        failed=0,
        shortlisted=0,
        percentage=0.0
    )

@router.get("/{session_id}/status", response_model=ProcessingStatusResponse)
def get_processing_status(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    total = session.total_candidates or 1
    pct = round((session.processed_candidates / total) * 100.0, 1) if session.total_candidates > 0 else 0.0
    if session.processing_status == "COMPLETED":
        pct = 100.0

    return ProcessingStatusResponse(
        session_id=session_id,
        status=session.processing_status,
        stage=session.current_stage or "INITIAL",
        total=session.total_candidates,
        processed=session.processed_candidates,
        failed=session.failed_candidates,
        shortlisted=session.shortlisted_candidates,
        percentage=pct
    )
