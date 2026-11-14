import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.database.schemas import ComplianceAnalyzeRequest, ComplianceReportOut, ComplianceReportSummary
from app.dependencies import get_current_user
from app.rag.ingestion import validate_pdf_bytes
from app.rag.pdf_processor import extract_pdf
from app.services import report_service
from app.utils.errors import AppError, NotFoundError

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


@router.post("/analyze")
async def analyze(
    payload: str = Form(..., description="JSON-encoded ComplianceAnalyzeRequest"),
    file: UploadFile | None = File(None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        request = ComplianceAnalyzeRequest.model_validate(json.loads(payload))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AppError("Invalid compliance request data.", status_code=422) from exc

    uploaded_text = ""
    if file is not None and file.filename:
        data = await file.read()
        try:
            validate_pdf_bytes(data, file.filename)
        except ValueError as exc:
            raise AppError(str(exc)) from exc
        # The user's technical document is processed in a temporary file and never indexed.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upload.pdf"
            path.write_bytes(data)
            uploaded_text = extract_pdf(path, extract_tables=False).full_text[:6000]
    return report_service.analyze_compliance(db, user, request, uploaded_text)


@router.get("/reports", response_model=list[ComplianceReportSummary])
def list_reports(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_user_reports(db, user.id, report_type="compliance")


@router.get("/reports/{report_id}", response_model=ComplianceReportOut)
def get_report(report_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = crud.get_user_report(db, user.id, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report
