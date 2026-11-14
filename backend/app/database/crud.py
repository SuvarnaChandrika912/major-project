"""Data-access helpers. Every user-owned query is scoped by user_id."""

from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import models
from app.database.models import utcnow


# ---------- Users ----------
def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.email == email.lower()))


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    hashed_password: str,
    preferred_language: str,
    organization: str | None,
    is_admin: bool,
) -> models.User:
    user = models.User(
        full_name=full_name.strip(),
        email=email.lower(),
        hashed_password=hashed_password,
        preferred_language=preferred_language,
        organization=organization,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_admins(db: Session) -> list[models.User]:
    return list(db.scalars(select(models.User).where(models.User.is_admin.is_(True))))


# ---------- Chat ----------
def create_session(db: Session, user_id: int, title: str) -> models.ChatSession:
    session = models.ChatSession(user_id=user_id, title=title[:255] or "New conversation")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_session(db: Session, user_id: int, session_id: int, with_messages: bool = False) -> models.ChatSession | None:
    stmt = select(models.ChatSession).where(
        models.ChatSession.id == session_id, models.ChatSession.user_id == user_id
    )
    if with_messages:
        stmt = stmt.options(selectinload(models.ChatSession.messages))
    return db.scalar(stmt)


def list_user_sessions(db: Session, user_id: int, limit: int = 50) -> list[models.ChatSession]:
    stmt = (
        select(models.ChatSession)
        .where(models.ChatSession.user_id == user_id)
        .order_by(models.ChatSession.updated_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def add_message(
    db: Session,
    *,
    session_id: int,
    role: str,
    message: str,
    agent_used: str | None = None,
    intent: str | None = None,
    extra: dict | None = None,
) -> models.ChatMessage:
    msg = models.ChatMessage(
        session_id=session_id, role=role, message=message, agent_used=agent_used, intent=intent, extra=extra
    )
    db.add(msg)
    session = db.get(models.ChatSession, session_id)
    if session:
        session.updated_at = utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def recent_history(db: Session, session_id: int, limit: int = 6) -> list[models.ChatMessage]:
    stmt = (
        select(models.ChatMessage)
        .where(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(list(db.scalars(stmt))))


def get_user_message(db: Session, user_id: int, message_id: int) -> models.ChatMessage | None:
    stmt = (
        select(models.ChatMessage)
        .join(models.ChatSession)
        .where(models.ChatMessage.id == message_id, models.ChatSession.user_id == user_id)
    )
    return db.scalar(stmt)


def upsert_feedback(db: Session, user_id: int, message_id: int, rating: int, comments: str | None) -> models.Feedback:
    fb = db.scalar(
        select(models.Feedback).where(models.Feedback.user_id == user_id, models.Feedback.message_id == message_id)
    )
    if fb is None:
        fb = models.Feedback(user_id=user_id, message_id=message_id, rating=rating, comments=comments)
        db.add(fb)
    else:
        fb.rating = rating
        fb.comments = comments
    db.commit()
    db.refresh(fb)
    return fb


# ---------- Notifications ----------
def create_notification(
    db: Session, user_id: int, title: str, description: str, notification_type: str = "info"
) -> models.Notification:
    n = models.Notification(
        user_id=user_id, title=title[:255], description=description, notification_type=notification_type
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def ingestion_notification_filter():
    return or_(
        models.Notification.notification_type.in_(("ingestion_success", "ingestion_error")),
        models.Notification.title.like("Indexed:%"),
        models.Notification.title.like("Ingestion failed:%"),
    )


# ---------- Reports ----------
def create_report(
    db: Session, *, user_id: int, product_name: str, report_title: str, report_type: str, report_data: dict
) -> models.ComplianceReport:
    report = models.ComplianceReport(
        user_id=user_id,
        product_name=product_name,
        report_title=report_title[:500],
        report_type=report_type,
        report_data=report_data,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_user_report(db: Session, user_id: int, report_id: int) -> models.ComplianceReport | None:
    return db.scalar(
        select(models.ComplianceReport).where(
            models.ComplianceReport.id == report_id, models.ComplianceReport.user_id == user_id
        )
    )


def list_user_reports(db: Session, user_id: int, report_type: str | None = None) -> list[models.ComplianceReport]:
    stmt = select(models.ComplianceReport).where(models.ComplianceReport.user_id == user_id)
    if report_type:
        stmt = stmt.where(models.ComplianceReport.report_type == report_type)
    return list(db.scalars(stmt.order_by(models.ComplianceReport.created_at.desc())))


# ---------- Dashboard ----------
def dashboard_summary(db: Session, user_id: int) -> dict:
    session_ids = select(models.ChatSession.id).where(models.ChatSession.user_id == user_id)
    total_sessions = db.scalar(select(func.count()).select_from(models.ChatSession).where(models.ChatSession.user_id == user_id)) or 0
    total_messages = db.scalar(
        select(func.count()).select_from(models.ChatMessage).where(
            models.ChatMessage.session_id.in_(session_ids), models.ChatMessage.role == "user"
        )
    ) or 0
    total_reports = db.scalar(
        select(func.count()).select_from(models.ComplianceReport).where(models.ComplianceReport.user_id == user_id)
    ) or 0
    unread = db.scalar(
        select(func.count()).select_from(models.Notification).where(
            models.Notification.user_id == user_id,
            models.Notification.read_status.is_(False),
            ingestion_notification_filter(),
        )
    ) or 0
    indexed_docs = db.scalar(
        select(func.count()).select_from(models.BISDocument).where(models.BISDocument.ingestion_status == "indexed")
    ) or 0

    since = utcnow() - timedelta(days=13)
    rows = db.execute(
        select(models.ChatMessage.created_at, models.ChatMessage.intent).where(
            models.ChatMessage.session_id.in_(session_ids),
            models.ChatMessage.role == "assistant",
            models.ChatMessage.created_at >= since,
        )
    ).all()
    per_day: dict[str, int] = {}
    for i in range(14):
        day = (since + timedelta(days=i)).date().isoformat()
        per_day[day] = 0
    intents: dict[str, int] = {}
    for created_at, intent in rows:
        key = created_at.date().isoformat()
        per_day[key] = per_day.get(key, 0) + 1
        if intent:
            intents[intent] = intents.get(intent, 0) + 1

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_reports": total_reports,
        "unread_notifications": unread,
        "indexed_documents": indexed_docs,
        "activity": [{"date": d, "queries": c} for d, c in sorted(per_day.items())],
        "intent_distribution": [{"intent": k, "count": v} for k, v in sorted(intents.items(), key=lambda x: -x[1])],
    }
