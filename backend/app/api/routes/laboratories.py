from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import models
from app.database.connection import get_db
from app.database.schemas import LaboratoryFilters, LaboratoryIn, LaboratoryOut
from app.dependencies import get_admin_user, get_current_user
from app.services import laboratory_service
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/api/laboratories", tags=["Laboratories"])


@router.get("")
def list_laboratories(
    q: str | None = None,
    state: str | None = None,
    city: str | None = None,
    capability: str | None = None,
    product_category: str | None = None,
    recognition: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = laboratory_service.search(db, q, state, city, capability, product_category, recognition, limit, offset)
    return {"total": total, "items": [LaboratoryOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.get("/filters", response_model=LaboratoryFilters)
def laboratory_filters(_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return laboratory_service.filters(db)


@router.get("/{laboratory_id}", response_model=LaboratoryOut)
def get_laboratory(laboratory_id: int, _user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    lab = db.get(models.Laboratory, laboratory_id)
    if lab is None:
        raise NotFoundError("Laboratory not found.")
    return lab


@router.post("", response_model=LaboratoryOut, status_code=status.HTTP_201_CREATED)
def create_laboratory(payload: LaboratoryIn, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    lab = models.Laboratory(**payload.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_laboratories(file: UploadFile = File(...), _admin: models.User = Depends(get_admin_user),
                              db: Session = Depends(get_db)) -> dict:
    count = laboratory_service.import_csv(db, await file.read())
    return {"imported": count}


@router.delete("/{laboratory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_laboratory(laboratory_id: int, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)) -> None:
    lab = db.get(models.Laboratory, laboratory_id)
    if lab is None:
        raise NotFoundError("Laboratory not found.")
    db.delete(lab)
    db.commit()
