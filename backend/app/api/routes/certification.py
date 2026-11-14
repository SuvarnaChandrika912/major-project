from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models
from app.database.connection import get_db
from app.database.schemas import CertificationGuidanceRequest, CertificationSchemeIn, CertificationSchemeOut
from app.dependencies import get_admin_user, get_current_user
from app.services import certification_service
from app.utils.errors import AppError, NotFoundError

router = APIRouter(prefix="/api/certification", tags=["Certification"])


@router.post("/guidance")
def certification_guidance(payload: CertificationGuidanceRequest, user: models.User = Depends(get_current_user),
                           db: Session = Depends(get_db)) -> dict:
    return certification_service.guidance(db, user, payload)


@router.get("/schemes", response_model=list[CertificationSchemeOut])
def list_schemes(_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(models.CertificationScheme).order_by(models.CertificationScheme.scheme_name)))


@router.post("/schemes", response_model=CertificationSchemeOut, status_code=status.HTTP_201_CREATED)
def create_scheme(payload: CertificationSchemeIn, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if db.scalar(select(models.CertificationScheme).where(models.CertificationScheme.scheme_name == payload.scheme_name)):
        raise AppError("A scheme with this name already exists.", status_code=409)
    scheme = models.CertificationScheme(**payload.model_dump())
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.put("/schemes/{scheme_id}", response_model=CertificationSchemeOut)
def update_scheme(scheme_id: int, payload: CertificationSchemeIn, _admin: models.User = Depends(get_admin_user),
                  db: Session = Depends(get_db)):
    scheme = db.get(models.CertificationScheme, scheme_id)
    if scheme is None:
        raise NotFoundError("Scheme not found.")
    for k, v in payload.model_dump().items():
        setattr(scheme, k, v)
    db.commit()
    return scheme


@router.delete("/schemes/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheme(scheme_id: int, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)) -> None:
    scheme = db.get(models.CertificationScheme, scheme_id)
    if scheme is None:
        raise NotFoundError("Scheme not found.")
    db.delete(scheme)
    db.commit()
