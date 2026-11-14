from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import report_agent
from app.database import crud, models
from app.database.schemas import ComplianceAnalyzeRequest, ReportGenerateRequest
from app.graph.state import AgentName, Intent
from app.graph.workflow import run_workflow
from app.utils.errors import AppError

_REPORT_PLANS = {
    "compliance": (Intent.COMPLIANCE_ASSESSMENT, [AgentName.PRODUCT.value, AgentName.COMPLIANCE.value, AgentName.STANDARDS.value]),
    "certification_roadmap": (Intent.CERTIFICATION_QUERY, [AgentName.PRODUCT.value, AgentName.CERTIFICATION.value,
                                                           AgentName.STANDARDS.value, AgentName.TESTING.value]),
    "standard_comparison": (Intent.STANDARD_COMPARISON, [AgentName.STANDARDS.value]),
    "laboratory_recommendation": (Intent.LABORATORY_SEARCH, [AgentName.PRODUCT.value, AgentName.TESTING.value]),
}

_REPORT_QUERIES = {
    "compliance": "Assess the compliance of {product} ({category}) against the applicable Indian Standard requirements. Specifications: {specs}",
    "certification_roadmap": "Create a BIS certification roadmap for {product} ({category}). Specifications: {specs}",
    "standard_comparison": "Compare the selected standards for {product}: scope, key requirements and test methods.",
    "laboratory_recommendation": "Identify testing requirements and recommend recognised laboratories for {product} ({category}).",
}


def _save(db: Session, user: models.User, report_type: str, product: str, inputs: dict, state: dict) -> models.ComplianceReport:
    citations = state.get("citations", [])
    content = report_agent.compose_report(report_type, product, state["final_response"], state.get("structured", {}),
                                          citations, state.get("verification", {}))
    report = crud.create_report(
        db, user_id=user.id, product_name=product,
        report_title=f"{report_agent.REPORT_TITLES[report_type]} - {product}", report_type=report_type,
        report_data={
            "inputs": inputs, "answer": state["final_response"], "content": content, "citations": citations,
            "verification": state.get("verification", {}), "structured": state.get("structured", {}),
            "agents_used": [f["agent"] for f in state.get("agent_findings", [])],
            "disclaimer": report_agent.DISCLAIMER,
        },
    )
    return report


def analyze_compliance(db: Session, user: models.User, req: ComplianceAnalyzeRequest, uploaded_text: str = "") -> dict:
    query = _REPORT_QUERIES["compliance"].format(product=req.product_name, category=req.product_category or "unspecified",
                                                 specs=req.specifications or "not provided")
    context = {
        "product_name": req.product_name, "product_category": req.product_category,
        "specifications": req.specifications, "available_documents": req.available_documents,
        "target_standard": req.target_standard, "uploaded_text": uploaded_text,
        "agents": _REPORT_PLANS["compliance"][1],
    }
    state = run_workflow(query, user_id=user.id, language=req.language, forced_intent=Intent.COMPLIANCE_ASSESSMENT.value,
                         context=context)
    compliance = state.get("structured", {}).get("compliance_agent", {})
    result = {
        "answer": state["final_response"], "citations": state.get("citations", []),
        "verification": state.get("verification", {}),
        "checklist": compliance.get("checklist", []), "status_counts": compliance.get("status_counts", {}),
        "missing_specifications": compliance.get("missing_specifications", []),
        "required_documents": compliance.get("required_documents", []),
        "agents_used": [f["agent"] for f in state.get("agent_findings", [])], "report_id": None,
    }
    if req.save_report:
        report = _save(db, user, "compliance", req.product_name, req.model_dump(), state)
        result["report_id"] = report.id
    return result


def generate(db: Session, user: models.User, req: ReportGenerateRequest) -> models.ComplianceReport:
    intent, agents = _REPORT_PLANS[req.report_type]
    context: dict = {"product_name": req.product_name, "product_category": req.product_category,
                     "specifications": req.specifications, "agents": agents, "state": req.state, "city": req.city}
    if req.report_type == "standard_comparison":
        if len(req.standard_ids) < 2:
            raise AppError("Select at least two standards to compare.")
        doc_ids = list(db.scalars(select(models.IndianStandard.document_id).where(
            models.IndianStandard.id.in_(req.standard_ids), models.IndianStandard.document_id.is_not(None))))
        if len(doc_ids) < 2:
            raise AppError("The selected standards do not have indexed documents.")
        context["document_ids"] = doc_ids
    query = _REPORT_QUERIES[req.report_type].format(product=req.product_name, category=req.product_category or "unspecified",
                                                    specs=req.specifications or "not provided")
    state = run_workflow(query, user_id=user.id, language=req.language, forced_intent=intent.value, context=context)
    return _save(db, user, req.report_type, req.product_name, req.model_dump(), state)


def pdf_for(report: models.ComplianceReport) -> bytes:
    return report_agent.render_pdf({
        "report_title": report.report_title, "product_name": report.product_name,
        "created_at": report.created_at, "report_data": report.report_data,
    })
