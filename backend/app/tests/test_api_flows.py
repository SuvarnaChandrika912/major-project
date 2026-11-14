import json

from app.database import crud
from app.services.auth_service import decode_access_token


def test_frontend_dev_origins_pass_cors_preflight(client):
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.options(
            "/api/auth/register",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_chat_persists_conversation(client, user_headers, indexed_document):
    resp = client.post("/api/chat/message", headers=user_headers,
                       json={"message": "What material is required for the synthetic widget?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["citations"] and body["message_id"] > 0
    assert "supervisor_agent" in body["agents_used"]

    sessions = client.get("/api/chat/sessions", headers=user_headers).json()
    assert any(s["id"] == body["session_id"] for s in sessions)
    detail = client.get(f"/api/chat/sessions/{body['session_id']}", headers=user_headers).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["extra"]["citations"]

    fb = client.post("/api/chat/feedback", headers=user_headers, json={"message_id": body["message_id"], "rating": 1})
    assert fb.status_code == 201


def test_users_cannot_see_others_sessions(client, user_headers, admin_headers, indexed_document, db):
    body = client.post("/api/chat/message", headers=user_headers, json={"message": "widget leakage test"}).json()
    admin_id = decode_access_token(admin_headers["Authorization"].removeprefix("Bearer "))
    admin_session = crud.create_session(db, admin_id, "Admin-only test conversation")

    member_sessions = client.get("/api/chat/sessions", headers=user_headers).json()
    admin_sessions = client.get("/api/chat/sessions", headers=admin_headers).json()
    assert body["session_id"] not in {session["id"] for session in admin_sessions}
    assert admin_session.id not in {session["id"] for session in member_sessions}
    assert admin_session.id in {session["id"] for session in admin_sessions}
    assert client.get(f"/api/chat/sessions/{body['session_id']}", headers=admin_headers).status_code == 404
    assert client.delete(f"/api/chat/sessions/{body['session_id']}", headers=admin_headers).status_code == 404


def test_notifications_only_show_document_ingestion_events(client, user_headers, db):
    user_id = decode_access_token(user_headers["Authorization"].removeprefix("Bearer "))
    crud.create_notification(db, user_id, "Welcome to BIS SAATHI", "Welcome message", "info")
    crud.create_notification(db, user_id, "Report ready", "Report message", "success")
    crud.create_notification(db, user_id, "Indexed: Legacy document", "Legacy success", "success")
    crud.create_notification(db, user_id, "Ingestion failed: Legacy document", "Legacy failure", "error")
    crud.create_notification(db, user_id, "New ingestion", "Indexed successfully", "ingestion_success")
    crud.create_notification(db, user_id, "Failed ingestion", "Indexing failed", "ingestion_error")

    notifications = client.get("/api/notifications", headers=user_headers).json()
    assert {item["title"] for item in notifications} == {
        "Indexed: Legacy document",
        "Ingestion failed: Legacy document",
        "New ingestion",
        "Failed ingestion",
    }


def test_compliance_report_generation_and_pdf(client, user_headers, indexed_document):
    payload = {"product_name": "Synthetic widget", "product_category": "widgets", "specifications": "Capacity 3 L",
               "save_report": True}
    resp = client.post("/api/compliance/analyze", headers=user_headers, data={"payload": json.dumps(payload)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["report_id"] and body["checklist"]

    report = client.get(f"/api/reports/{body['report_id']}", headers=user_headers).json()
    assert report["report_type"] == "compliance"
    pdf = client.get(f"/api/reports/{body['report_id']}/download", headers=user_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    notifications = client.get("/api/notifications", headers=user_headers).json()
    assert not any(item["title"] == "Report ready" for item in notifications)
    assert client.delete(f"/api/reports/{body['report_id']}", headers=user_headers).status_code == 204


def test_standards_search_and_detail(client, user_headers, indexed_document):
    resp = client.get("/api/standards/search", headers=user_headers, params={"q": "IS 99999"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results and results[0]["standard_number"] == "IS 99999:2024"
    std_id = results[0]["standard"]["id"]
    detail = client.get(f"/api/standards/{std_id}", headers=user_headers).json()
    assert detail["clauses"]


def test_laboratory_import_and_search(client, admin_headers, user_headers):
    csv_data = ("laboratory_name,city,state,recognition_status,testing_capabilities\n"
                "Synthetic Test Lab (FIXTURE),Pune,Maharashtra,Test fixture,widget leakage testing\n")
    resp = client.post("/api/laboratories/import", headers=admin_headers,
                       files={"file": ("labs.csv", csv_data.encode(), "text/csv")})
    assert resp.status_code == 201 and resp.json()["imported"] == 1
    found = client.get("/api/laboratories", headers=user_headers, params={"capability": "leakage"}).json()
    assert found["total"] >= 1
    filters = client.get("/api/laboratories/filters", headers=user_headers).json()
    assert "Maharashtra" in filters["states"]


def test_document_upload_validation(client, admin_headers):
    bad = client.post("/api/documents/upload", headers=admin_headers,
                      data={"document_title": "Not a pdf", "document_type": "faq"},
                      files={"file": ("a.pdf", b"hello", "application/pdf")})
    assert bad.status_code == 400


def test_dashboard_and_health(client, user_headers):
    summary = client.get("/api/dashboard/summary", headers=user_headers)
    assert summary.status_code == 200 and len(summary.json()["activity"]) == 14
    health = client.get("/api/health").json()
    assert health["database"] == "connected"
