from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import models
from app.database.connection import get_db
from app.database.schemas import StandardCompareRequest, StandardDetail, StandardSearchResponse
from app.dependencies import get_current_user
from app.services import standards_service

router = APIRouter(prefix="/api/standards", tags=["Standards"])


@router.get("/search", response_model=StandardSearchResponse)
def search_standards(
    q: str = Query(..., min_length=1, max_length=500),
    mode: standards_service.SearchMode = "auto",
    status: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return standards_service.search(db, q, mode, status, limit)


@router.post("/compare")
def compare_standards(payload: StandardCompareRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return standards_service.compare(db, user.id, payload.standard_ids, payload.focus, payload.language)


@router.get("/{standard_id}", response_model=StandardDetail)
def get_standard(standard_id: int, _user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return standards_service.get_standard(db, standard_id)
