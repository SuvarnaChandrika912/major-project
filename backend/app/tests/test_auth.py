from app.services.auth_service import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing_roundtrip():
    hashed = hash_password("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert verify_password("Sup3rSecret!", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip():
    token, expires = create_access_token(42)
    assert expires > 0
    assert decode_access_token(token) == 42


def test_register_login_me(client):
    resp = client.post("/api/auth/register", json={"full_name": "Asha", "email": "asha@example.com", "password": "Password123!"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["is_admin"] is False

    dup = client.post("/api/auth/register", json={"full_name": "Asha", "email": "asha@example.com", "password": "Password123!"})
    assert dup.status_code == 409

    bad = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "nope-nope"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "Password123!"})
    token = ok.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["full_name"] == "Asha"


def test_protected_route_requires_token(client):
    assert client.get("/api/chat/sessions").status_code == 401
    assert client.get("/api/chat/sessions", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_admin_from_config(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert me["is_admin"] is True


def test_non_admin_cannot_upload(client, user_headers):
    resp = client.post("/api/documents/upload", headers=user_headers,
                       data={"document_title": "x doc", "document_type": "faq"},
                       files={"file": ("a.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert resp.status_code == 403


def test_profile_update(client, user_headers):
    resp = client.patch("/api/auth/me", headers=user_headers, json={"preferred_language": "hi", "organization": "Test MSME"})
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "hi"
    client.patch("/api/auth/me", headers=user_headers, json={"preferred_language": "en"})
