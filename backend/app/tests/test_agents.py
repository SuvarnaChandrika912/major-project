from app.agents import translation_agent
from app.agents.supervisor_agent import INTENT_AGENTS, keyword_intent
from app.agents.verification_agent import deterministic_checks, verify
from app.graph.routing import dispatch_specialists, route_after_supervisor
from app.graph.state import Intent
from app.graph.workflow import run_workflow
from app.rag.retrieval import retrieve
from app.services.llm_service import set_llm
from app.tests.fakes import FakeLLM


def test_keyword_intent_classification():
    assert keyword_intent("How do I verify HUID on gold jewellery?") == Intent.HALLMARKING_QUERY
    assert keyword_intent("Compare IS 1 and IS 2") == Intent.STANDARD_COMPARISON
    assert keyword_intent("Find a testing laboratory in Pune") == Intent.LABORATORY_SEARCH
    assert keyword_intent("What does BIS do?") == Intent.GENERAL_BIS_QUERY


def test_simple_queries_route_to_single_agent():
    assert INTENT_AGENTS[Intent.HALLMARKING_QUERY] == ["consumer_agent"]
    assert route_after_supervisor({"selected_agents": ["consumer_agent"]})[0].node == "consumer_agent"


def test_product_agent_runs_before_specialists():
    assert route_after_supervisor({"selected_agents": ["product_agent", "standards_agent"]}) == "product_agent"
    sends = dispatch_specialists({"selected_agents": ["product_agent", "standards_agent", "compliance_agent"]})
    assert sorted(s.node for s in sends) == ["compliance_agent", "standards_agent"]
    assert dispatch_specialists({"selected_agents": []}) == "collect_evidence"


def test_language_detection_and_identifier_preservation():
    assert translation_agent.detect_language("हॉलमार्किंग क्या है?") == "hi"
    assert translation_agent.detect_language("హాల్‌మార్కింగ్ అంటే ఏమిటి") == "te"
    assert translation_agent.detect_language("What is hallmarking?") == "en"
    masked, protected = translation_agent.mask_identifiers("See IS 99999:2024 Clause 4.1 [2] and HUID.")
    assert "IS 99999" not in masked and len(protected) == 4
    restored, ok = translation_agent.unmask_identifiers(masked, protected)
    assert ok and restored == "See IS 99999:2024 Clause 4.1 [2] and HUID."


def test_verification_rejects_fabricated_references(indexed_document):
    chunks = retrieve("stainless steel", top_k=2).chunks
    claims = ["Clause 4.1 requires stainless steel [1]", "IS 55555 also applies [1]", "Uncited claim", "Bad marker [7]"]
    to_judge, unsupported, _ = deterministic_checks(claims, chunks)
    assert to_judge == ["Clause 4.1 requires stainless steel [1]"]
    assert len(unsupported) == 3


def test_verification_without_evidence_is_insufficient():
    result = verify("question", ["claim [1]"], [])
    assert result.evidence_status == "INSUFFICIENT"


def test_full_workflow_produces_grounded_answer(indexed_document):
    state = run_workflow("Which standard applies to a stainless steel widget?")
    assert state["intent"] == Intent.PRODUCT_STANDARD_SEARCH.value
    agents = [f["agent"] for f in state["agent_findings"]]
    assert agents[0] == "product_agent" and "standards_agent" in agents
    assert "[1]" in state["final_response"] and "[42]" not in state["final_response"]
    assert state["citations"] and state["citations"][0]["standard_number"] == "IS 99999:2024"
    assert state["verification"]["evidence_status"] in {"SUFFICIENT", "PARTIAL"}
    # Hallucinated standard numbers from the LLM are filtered out of structured output.
    assert state["structured"]["standards_agent"]["relevant_standards"] == ["IS 99999:2024"]


def test_compliance_agent_drops_unverifiable_clauses(indexed_document):
    state = run_workflow("Check compliance", forced_intent=Intent.COMPLIANCE_ASSESSMENT.value,
                         context={"product_name": "widget", "specifications": "capacity 3 litres"})
    checklist = state["structured"]["compliance_agent"]["checklist"]
    invented = next(i for i in checklist if i["requirement"] == "Invented requirement")
    assert invented["clause_number"] is None


def test_workflow_degrades_gracefully_without_llm(indexed_document):
    set_llm(FakeLLM(available=False))
    state = run_workflow("stainless steel widget material requirements")
    assert "language model is unavailable" in state["final_response"]
    assert state["citations"]
