from fastapi import APIRouter
from backend.app.api.sessions import router as sessions_router
from backend.app.api.candidates import router as candidates_router

api_router = APIRouter(prefix="/api")
api_router.include_router(sessions_router)
api_router.include_router(candidates_router)
