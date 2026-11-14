from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.schemas import CertificationGuidanceRequest
from app.graph.state import AgentName, Intent
from app.graph.workflow import run_workflow


def guidance(db: Session, user: models.User, req: CertificationGuidanceRequest) -> dict:
    location = "in India" if req.manufacturing_location == "india" else f"outside India ({req.manufacturing_country or 'country not specified'})"
    query = (
        f"Provide a BIS certification roadmap for '{req.product_name}' (category: {req.product_category}), "
        f"manufactured {location} by a {req.organization_type}. Existing certification: {req.existing_certification}. "
        f"Specifications: {req.product_specifications or 'not provided'}. Identify candidate certification schemes, "
        "applicable standards, required documents, testing guidance and the step-by-step process."
    )
    context = {
        "product_name": req.product_name,
        "product_category": req.product_category,
        "manufacturing_location": location,
        "organization_type": req.organization_type,
        "existing_certification": req.existing_certification,
        "specifications": req.product_specifications,
        "agents": [AgentName.PRODUCT.value, AgentName.CERTIFICATION.value, AgentName.STANDARDS.value, AgentName.TESTING.value],
    }
    state = run_workflow(query, user_id=user.id, language=req.language, forced_intent=Intent.CERTIFICATION_QUERY.value,
                         context=context)
    structured = state.get("structured", {})
    result = {
        "answer": state["final_response"],
        "citations": state.get("citations", []),
        "verification": state.get("verification", {}),
        "follow_up_questions": state.get("follow_up_questions", []),
        "clarification_questions": state.get("clarification_questions", []),
        "candidate_schemes": structured.get("certification_agent", {}).get("candidate_schemes", []),
        "documentation_checklist": structured.get("certification_agent", {}).get("documentation_checklist", []),
        "process_steps": structured.get("certification_agent", {}).get("process_steps", []),
        "official_links": structured.get("certification_agent", {}).get("official_links", []),
        "applicable_standards": structured.get("standards_agent", {}).get("relevant_standards", [])
        or [c["standard_number"] for c in structured.get("product_agent", {}).get("candidate_standards", [])],
        "required_tests": structured.get("testing_agent", {}).get("required_tests", []),
        "agents_used": [f["agent"] for f in state.get("agent_findings", [])],
        "report_id": None,
    }
    if req.save_report:
        report = crud.create_report(
            db, user_id=user.id, product_name=req.product_name,
            report_title=f"Certification Roadmap - {req.product_name}", report_type="certification_roadmap",
            report_data={"inputs": req.model_dump(), **result, "structured": structured,
                         "content": {"executive_summary": state["final_response"]}},
        )
        result["report_id"] = report.id
    return result
