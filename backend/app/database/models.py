from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[list["ComplianceReport"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    agent_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Citations, verification result, follow-ups and agent trace for assistant messages.
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class BISDocument(Base):
    __tablename__ = "bis_documents"
    __table_args__ = (
        UniqueConstraint("file_hash", name="uq_bis_documents_file_hash"),
        Index("ix_bis_documents_standard_version", "standard_number", "document_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_title: Mapped[str] = mapped_column(String(500))
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    standard_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    document_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amendment_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    file_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    ingestion_status: Mapped[str] = mapped_column(String(30), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunk text and structural metadata (no embeddings) used for BM25, clause views and citations."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("bis_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[BISDocument] = relationship(back_populates="chunks")


class IndianStandard(Base):
    __tablename__ = "indian_standards"
    __table_args__ = (UniqueConstraint("standard_number", "amendment_number", "document_id", name="uq_standard_doc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_number: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amendment_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="current", index=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("bis_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )


class CertificationScheme(Base):
    __tablename__ = "certification_schemes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Laboratory(Base):
    __tablename__ = "laboratories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    laboratory_name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    contact_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    recognition_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    testing_capabilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    report_title: Mapped[str] = mapped_column(String(500))
    report_type: Mapped[str] = mapped_column(String(50), default="compliance")
    report_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="reports")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[str] = mapped_column(String(50), default="info")
    read_status: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="notifications")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_feedback_user_message"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
