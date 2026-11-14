import re

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.database.schemas import ComplianceReportOut, ComplianceReportSummary, DashboardSummary, ReportGenerateRequest
from app.dependencies import get_current_user
from app.services import report_service
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/api", tags=["Reports"])


@router.post("/reports/generate", response_model=ComplianceReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(payload: ReportGenerateRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_service.generate(db, user, payload)


@router.get("/reports", response_model=list[ComplianceReportSummary])
def list_reports(report_type: str | None = None, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_user_reports(db, user.id, report_type)


@router.get("/reports/{report_id}", response_model=ComplianceReportOut)
def get_report(report_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = crud.get_user_report(db, user.id, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    report = crud.get_user_report(db, user.id, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", report.report_title)[:80] + ".pdf"
    return Response(
        content=report_service.pdf_for(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    report = crud.get_user_report(db, user.id, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    db.delete(report)
    db.commit()


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.dashboard_summary(db, user.id)
