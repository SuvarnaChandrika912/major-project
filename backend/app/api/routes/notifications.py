from fastapi import APIRouter, Depends, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.database.schemas import NotificationOut
from app.dependencies import get_current_user
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(unread_only: bool = False, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(models.Notification).where(
        models.Notification.user_id == user.id,
        crud.ingestion_notification_filter(),
    )
    if unread_only:
        stmt = stmt.where(models.Notification.read_status.is_(False))
    return list(db.scalars(stmt.order_by(models.Notification.created_at.desc()).limit(100)))


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(models.Notification).where(
        models.Notification.id == notification_id,
        models.Notification.user_id == user.id,
        crud.ingestion_notification_filter(),
    ))
    if n is None:
        raise NotFoundError("Notification not found.")
    n.read_status = True
    db.commit()
    return n


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    db.execute(update(models.Notification).where(
        models.Notification.user_id == user.id,
        crud.ingestion_notification_filter(),
    ).values(read_status=True))
    db.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(notification_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    n = db.scalar(select(models.Notification).where(
        models.Notification.id == notification_id,
        models.Notification.user_id == user.id,
        crud.ingestion_notification_filter(),
    ))
    if n is None:
        raise NotFoundError("Notification not found.")
    db.delete(n)
    db.commit()
