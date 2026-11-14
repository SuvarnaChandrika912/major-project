"""Test configuration.

Tests run against a throwaway SQLite database and in-process fakes for the LLM, embedder and
Pinecone so they work offline. Set TEST_DATABASE_URL to a MySQL URL to run them against MySQL.
All BIS content used here is SYNTHETIC FIXTURE DATA and is not official BIS information.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TEST_DB = ROOT / "test_bis_saathi.db"

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256-signing"
os.environ["PINECONE_API_KEY"] = ""
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["UPLOAD_DIR"] = str(ROOT / "data" / "test_uploads")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import models  # noqa: E402
from app.database.connection import Base, SessionLocal, engine  # noqa: E402
from app.rag.embeddings import set_embedder  # noqa: E402
from app.services.llm_service import set_llm  # noqa: E402
from app.tests.fakes import FakeEmbedder, FakeLLM  # noqa: E402

SYNTHETIC_TEXT = """SYNTHETIC FIXTURE - NOT OFFICIAL BIS DATA
IS 99999 : 2024
SYNTHETIC TEST WIDGET - SPECIFICATION
1 SCOPE
This synthetic standard covers test widgets used only in automated tests.
2 REFERENCES
No references.
4 REQUIREMENTS
4.1 Material
The widget body shall be made of food grade stainless steel.
4.2 Capacity
The rated capacity shall be not less than 2 litres.
5 TESTS
5.1 Leakage Test
The widget shall be filled with water and inspected for leakage for 30 minutes.
"""


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    if TEST_DB.exists():
        try:
            TEST_DB.unlink()
        except PermissionError:
            pass


@pytest.fixture(autouse=True)
def _fakes():
    set_llm(FakeLLM())
    set_embedder(FakeEmbedder())
    yield
    set_llm(None)
    set_embedder(None)


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def _register(client: TestClient, email: str) -> str:
    resp = client.post("/api/auth/register", json={"full_name": "Test User", "email": email, "password": "Password123!"})
    if resp.status_code == 409:
        resp = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def user_headers(client):
    return {"Authorization": f"Bearer {_register(client, 'user@example.com')}"}


@pytest.fixture()
def admin_headers(client):
    return {"Authorization": f"Bearer {_register(client, 'admin@example.com')}"}


@pytest.fixture()
def indexed_document(db):
    """Insert a synthetic, already-indexed standard with structural chunks."""
    from app.rag.chunking import chunk_pages
    from app.rag.pdf_processor import PageContent

    existing = db.query(models.BISDocument).filter_by(file_hash="synthetic-hash").first()
    if existing:
        return existing
    doc = models.BISDocument(
        document_title="Synthetic Test Widget - Specification (TEST FIXTURE)",
        document_type="indian_standard", standard_number="IS 99999:2024", document_version="2024",
        file_path="synthetic.pdf", file_hash="synthetic-hash", status="current", ingestion_status="indexed",
    )
    db.add(doc)
    db.commit()
    chunks = chunk_pages([PageContent(page_number=1, text=SYNTHETIC_TEXT)])
    for c in chunks:
        db.add(models.DocumentChunk(chunk_id=f"doc{doc.id}-c{c.chunk_index}", document_id=doc.id,
                                    chunk_index=c.chunk_index, section=c.section, clause_number=c.clause_number,
                                    page_number=c.page_number, text=c.text))
    db.add(models.IndianStandard(standard_number="IS 99999:2024", title=doc.document_title,
                                 scope="Synthetic test widgets", status="current", document_id=doc.id))
    db.commit()
    return doc
