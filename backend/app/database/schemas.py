from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

SupportedLanguage = Literal["en", "hi", "te", "kn", "ta"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    preferred_language: SupportedLanguage = "en"
    organization: str | None = Field(default=None, max_length=200)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: SupportedLanguage | None = None
    organization: str | None = Field(default=None, max_length=200)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    full_name: str
    email: EmailStr
    preferred_language: str
    organization: str | None
    is_admin: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------- RAG / citations ----------
class Citation(BaseModel):
    index: int
    chunk_id: str
    document_id: int | None = None
    standard_number: str | None = None
    standard_title: str | None = None
    clause_number: str | None = None
    section: str | None = None
    page_number: int | None = None
    document_version: str | None = None
    amendment_number: str | None = None
    document_status: str | None = None
    document_type: str | None = None
    source_url: str | None = None
    excerpt: str = ""
    score: float | None = None


class VerificationResult(BaseModel):
    evidence_status: Literal["SUFFICIENT", "PARTIAL", "INSUFFICIENT"] = "INSUFFICIENT"
    confidence: float = 0.0
    supported_claims: list[str] = []
    unsupported_claims: list[str] = []
    warnings: list[str] = []
    outdated_documents: list[str] = []


class AgentTrace(BaseModel):
    agent: str
    status: Literal["completed", "failed", "skipped", "timeout"]
    summary: str = ""
    duration_ms: int = 0


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None
    language: SupportedLanguage | None = None


class ChatResponse(BaseModel):
    session_id: int
    message_id: int
    answer: str
    intent: str
    language: str
    agents_used: list[str]
    citations: list[Citation]
    verification: VerificationResult
    follow_up_questions: list[str]
    clarification_questions: list[str] = []
    agent_trace: list[AgentTrace]
    structured: dict[str, Any] = {}


class ChatMessageOut(ORMModel):
    id: int
    role: str
    message: str
    agent_used: str | None
    intent: str | None
    extra: dict | None
    created_at: datetime


class ChatSessionOut(ORMModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut]


class FeedbackCreate(BaseModel):
    message_id: int
    rating: int = Field(ge=-1, le=1)
    comments: str | None = Field(default=None, max_length=2000)


# ---------- Documents ----------
DocumentType = Literal[
    "indian_standard",
    "certification_guideline",
    "hallmarking",
    "faq",
    "laboratory_information",
    "other",
]


class DocumentOut(ORMModel):
    id: int
    document_title: str
    document_type: str
    standard_number: str | None
    document_version: str | None
    amendment_number: str | None
    publication_date: date | None
    source_url: str | None
    status: str
    ingestion_status: str
    error_message: str | None
    page_count: int
    chunk_count: int
    used_ocr: bool
    created_at: datetime


class DocumentChunkOut(ORMModel):
    chunk_id: str
    chunk_index: int
    section: str | None
    clause_number: str | None
    page_number: int
    text: str


class DocumentDetail(DocumentOut):
    chunks: list[DocumentChunkOut] = []


# ---------- Standards ----------
class StandardOut(ORMModel):
    id: int
    standard_number: str
    title: str
    scope: str | None
    publication_date: date | None
    amendment_number: str | None
    status: str
    document_id: int | None


class StandardSearchHit(BaseModel):
    standard: StandardOut | None = None
    document_id: int | None = None
    standard_number: str | None = None
    title: str | None = None
    status: str | None = None
    matched_clauses: list[Citation] = []
    score: float | None = None


class StandardSearchResponse(BaseModel):
    query: str
    mode: str
    results: list[StandardSearchHit]
    message: str | None = None


class StandardDetail(StandardOut):
    document: DocumentOut | None = None
    clauses: list[DocumentChunkOut] = []


class StandardCompareRequest(BaseModel):
    standard_ids: list[int] = Field(min_length=2, max_length=4)
    focus: str | None = Field(default=None, max_length=500)
    language: SupportedLanguage | None = None


# ---------- Certification ----------
class CertificationSchemeIn(BaseModel):
    scheme_name: str = Field(min_length=2, max_length=255)
    description: str
    requirements: str | None = None
    official_source_url: str | None = None


class CertificationSchemeOut(ORMModel):
    id: int
    scheme_name: str
    description: str
    requirements: str | None
    official_source_url: str | None


class CertificationGuidanceRequest(BaseModel):
    product_category: str = Field(min_length=2, max_length=200)
    product_name: str = Field(min_length=2, max_length=200)
    manufacturing_location: Literal["india", "outside_india"] = "india"
    manufacturing_country: str | None = Field(default=None, max_length=100)
    product_specifications: str = Field(default="", max_length=4000)
    existing_certification: str = Field(default="none", max_length=500)
    organization_type: str = Field(default="msme", max_length=100)
    language: SupportedLanguage | None = None
    save_report: bool = False


# ---------- Laboratories ----------
class LaboratoryIn(BaseModel):
    laboratory_name: str = Field(min_length=2, max_length=255)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    contact_information: str | None = None
    recognition_status: str | None = None
    testing_capabilities: str | None = None
    product_categories: str | None = None
    official_source_url: str | None = None
    last_verified_at: datetime | None = None


class LaboratoryOut(ORMModel):
    id: int
    laboratory_name: str
    address: str | None
    city: str | None
    state: str | None
    contact_information: str | None
    recognition_status: str | None
    testing_capabilities: str | None
    product_categories: str | None
    official_source_url: str | None
    last_verified_at: datetime | None


class LaboratoryFilters(BaseModel):
    states: list[str]
    cities: list[str]


# ---------- Hallmarking / consumer ----------
class AssistantQuery(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    language: SupportedLanguage | None = None


class AssistantAnswer(BaseModel):
    answer: str
    intent: str
    citations: list[Citation]
    verification: VerificationResult
    follow_up_questions: list[str]
    official_resources: list[dict[str, str]] = []
    agents_used: list[str] = []


# ---------- Compliance ----------
class ComplianceAnalyzeRequest(BaseModel):
    product_name: str = Field(min_length=2, max_length=200)
    product_category: str = Field(default="", max_length=200)
    specifications: str = Field(default="", max_length=8000)
    available_documents: list[str] = []
    target_standard: str | None = Field(default=None, max_length=100)
    language: SupportedLanguage | None = None
    save_report: bool = True


class ComplianceReportOut(ORMModel):
    id: int
    product_name: str
    report_title: str
    report_type: str
    report_data: dict
    created_at: datetime


class ComplianceReportSummary(ORMModel):
    id: int
    product_name: str
    report_title: str
    report_type: str
    created_at: datetime


# ---------- Reports ----------
ReportType = Literal["compliance", "certification_roadmap", "standard_comparison", "laboratory_recommendation"]


class ReportGenerateRequest(BaseModel):
    report_type: ReportType
    product_name: str = Field(min_length=2, max_length=200)
    product_category: str = Field(default="", max_length=200)
    specifications: str = Field(default="", max_length=8000)
    standard_ids: list[int] = []
    state: str | None = None
    city: str | None = None
    language: SupportedLanguage | None = None


# ---------- Notifications ----------
class NotificationOut(ORMModel):
    id: int
    title: str
    description: str
    notification_type: str
    read_status: bool
    created_at: datetime


# ---------- Dashboard ----------
class DashboardSummary(BaseModel):
    total_sessions: int
    total_messages: int
    total_reports: int
    unread_notifications: int
    indexed_documents: int
    activity: list[dict[str, Any]]
    intent_distribution: list[dict[str, Any]]


class HealthStatus(BaseModel):
    status: str
    database: str
    pinecone: str
    llm: str
    embedding_model: str
