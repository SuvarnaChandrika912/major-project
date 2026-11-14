import csv
import io
from datetime import datetime

from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session

from app.database import models
from app.database.schemas import LaboratoryIn
from app.utils.errors import AppError

CSV_FIELDS = list(LaboratoryIn.model_fields.keys())


def search(db: Session, q: str | None, state: str | None, city: str | None, capability: str | None,
           product_category: str | None, recognition: str | None, limit: int, offset: int) -> tuple[list[models.Laboratory], int]:
    stmt = select(models.Laboratory)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(models.Laboratory.laboratory_name.ilike(like), models.Laboratory.testing_capabilities.ilike(like),
                              models.Laboratory.product_categories.ilike(like), models.Laboratory.address.ilike(like)))
    if state:
        stmt = stmt.where(models.Laboratory.state == state)
    if city:
        stmt = stmt.where(models.Laboratory.city == city)
    if capability:
        stmt = stmt.where(models.Laboratory.testing_capabilities.ilike(f"%{capability}%"))
    if product_category:
        stmt = stmt.where(models.Laboratory.product_categories.ilike(f"%{product_category}%"))
    if recognition:
        stmt = stmt.where(models.Laboratory.recognition_status.ilike(f"%{recognition}%"))
    total = len(db.scalars(stmt.with_only_columns(models.Laboratory.id)).all())
    rows = db.scalars(stmt.order_by(models.Laboratory.laboratory_name).limit(limit).offset(offset)).all()
    return list(rows), total


def filters(db: Session) -> dict[str, list[str]]:
    states = [s for s in db.scalars(select(distinct(models.Laboratory.state)).order_by(models.Laboratory.state)) if s]
    cities = [c for c in db.scalars(select(distinct(models.Laboratory.city)).order_by(models.Laboratory.city)) if c]
    return {"states": states, "cities": cities}


def import_csv(db: Session, data: bytes) -> int:
    """Import laboratory records from an administrator-supplied CSV of verified official data."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "laboratory_name" not in reader.fieldnames:
        raise AppError(f"CSV must include a 'laboratory_name' column. Supported columns: {', '.join(CSV_FIELDS)}")
    count = 0
    for row in reader:
        clean = {k: (row.get(k) or "").strip() or None for k in CSV_FIELDS if k in row}
        if not clean.get("laboratory_name"):
            continue
        if clean.get("last_verified_at"):
            try:
                clean["last_verified_at"] = datetime.fromisoformat(clean["last_verified_at"])
            except ValueError:
                clean["last_verified_at"] = None
        payload = LaboratoryIn(**clean)
        existing = db.scalar(select(models.Laboratory).where(
            models.Laboratory.laboratory_name == payload.laboratory_name, models.Laboratory.city == payload.city))
        lab = existing or models.Laboratory()
        for key, value in payload.model_dump().items():
            setattr(lab, key, value)
        db.add(lab)
        count += 1
    db.commit()
    return count
