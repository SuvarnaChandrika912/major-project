# BIS SAATHI — Backend

FastAPI service for **BIS SAATHI**, an agentic AI assistant for Indian Standards, BIS certification, hallmarking and consumer guidance. Answers are produced by a LangGraph multi-agent workflow over a retrieval-augmented knowledge base built only from documents an administrator uploads.

> BIS SAATHI is an academic project and is not an official Bureau of Indian Standards service. Always confirm requirements on [bis.gov.in](https://www.bis.gov.in) or [manakonline.in](https://www.manakonline.in).

## Architecture

```
Next.js frontend ──HTTP/JWT──► FastAPI (app/main.py)
                                 │
                                 ├── MySQL (users, chats, documents, chunks, standards, schemes, labs, reports, notifications)
                                 ├── Pinecone (dense vectors, llama-text-embed-v2 hosted inference)
                                 ├── Groq API (default LLM) or Ollama when LLM_PROVIDER=ollama
                                 └── LangGraph workflow (app/graph)
```

Workflow for every question (`app/graph/workflow.py`):

1. **receive_query → detect_language → translate_query**: Hindi, Tamil, Telugu and Kannada are detected from the script and translated to English. IS numbers, clause numbers, HUID/ISI terms and URLs are protected during translation.
2. **supervisor**: classifies intent (standards, certification, testing, hallmarking, consumer, compliance, comparison, product, general) and plans which agents run. Falls back to keyword routing if the LLM is unavailable.
3. **product_agent** (when needed) extracts a product specification first; then the selected **specialist agents run in parallel** (standards, certification, testing, consumer, compliance).
4. **collect_evidence**: merges each agent's evidence into one global, numbered citation list.
5. **verification**: deterministic checks (citation present and in range, IS numbers and amounts actually appear in the evidence, superseded documents, prompt-injection text) followed by an LLM judgement: `SUFFICIENT`, `PARTIAL` or `INSUFFICIENT`. If evidence is insufficient, retrieval is expanded once and verification re-runs.
6. **generate_response → translate_response → save_conversation**.

Retrieval (`app/rag/retrieval.py`) is hybrid: Pinecone dense search plus BM25 over the MySQL chunk table, fused with reciprocal rank fusion, optionally re-ranked with a cross-encoder, and enriched with each document's current status from MySQL.

Graceful degradation: if the LLM provider is down or not configured, the API still returns the most relevant passages with citations and says the AI model is unavailable. If Pinecone is not configured, retrieval uses BM25 only and `/api/health` reports it. No mock answers are ever generated.

## Prerequisites

| Component | Version | Notes |
| --- | --- | --- |
| Python | 3.11 or 3.12 | PyTorch wheels are not yet available for every newer Python |
| MySQL | 8.x | Any account that can create tables in one database |
| Pinecone | Free Starter account | Serverless index is created automatically |
| Groq API key | — | [console.groq.com](https://console.groq.com/keys) (default `LLM_PROVIDER=groq`) |
| Ollama | optional | Only if `LLM_PROVIDER=ollama` |
| Tesseract OCR | 5.x | Only needed for scanned PDFs |

## Setup on Windows (PowerShell)

```powershell
cd backend

# 1. Virtual environment and dependencies
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 2. MySQL database (enter your MySQL root password when prompted)
mysql -u root -p -e "CREATE DATABASE bis_saathi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'bis_saathi'@'localhost' IDENTIFIED BY 'choose-a-strong-password'; GRANT ALL PRIVILEGES ON bis_saathi.* TO 'bis_saathi'@'localhost'; FLUSH PRIVILEGES;"

# 3. Groq API key (add to .env as GROQ_API_KEY — see project root .env)

# 4. Tesseract OCR (optional, for scanned PDFs)
winget install UB-Mannheim.TesseractOCR

# 5. Environment file (project root .env is loaded automatically)
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste the output into JWT_SECRET_KEY
notepad .env
```

Fill in at least `MYSQL_USER`, `MYSQL_PASSWORD`, `PINECONE_API_KEY`, `JWT_SECRET_KEY` and `ADMIN_EMAILS` (the email you will register with, so you can upload documents). On Windows set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`.

```powershell
# 6. Apply the checked-in database schema
alembic upgrade head

# 7. Run the API
uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health (reports database, Pinecone, LLM and embedding model status)

Embeddings are generated through Pinecone Inference with `llama-text-embed-v2` (1024 dimensions). The dense Pinecone index must use the same dimension and cosine metric.

The application writes and updates data rows as users register, upload documents and use features; no manual SQL is needed for routine data. When the database structure changes, update the SQLAlchemy models, generate a migration with `alembic revision --autogenerate -m "describe change"`, then apply it with `alembic upgrade head`.

### Windows Smart App Control

If Python fails with `DLL load failed ... An Application Control policy has blocked this file`, Windows **Smart App Control** is blocking native extensions inside the virtual environment (seen with SQLAlchemy and `uuid_utils`, which `langchain-core` needs). Options:

- Run the backend on a machine (or WSL/Linux/Docker) without Smart App Control, or
- Turn Smart App Control off in *Windows Security → App & browser control → Smart App Control settings*. On many Windows versions it cannot be turned back on without resetting Windows.

For SQLAlchemy alone, `$env:DISABLE_SQLALCHEMY_CEXT_RUNTIME="1"` switches to the pure-Python implementation, but LangChain still needs `uuid_utils`.

## Setup on Linux / macOS

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
sudo apt install tesseract-ocr          # macOS: brew install tesseract
# Set GROQ_API_KEY in the project root .env
cp .env.example .env                    # then edit it
alembic revision --autogenerate -m "initial schema"   # first time only
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Building the knowledge base

The system ships with **no BIS content**. Sign in with an email listed in `ADMIN_EMAILS`, open **Knowledge Base** in the frontend and upload PDFs you are authorised to use (Indian Standards, certification guidelines, hallmarking guidelines, consumer guidance, laboratory directories).

Each upload is validated (PDF signature, size limit, duplicate hash), then processed in the background: text and tables are extracted with PyMuPDF (OCR for scanned pages), split into clause-aware chunks, embedded, upserted to Pinecone and stored in MySQL. Uploading a new version of the same standard number marks older versions as superseded.

Structured records that the agents cite directly:

- **Certification schemes**: added by admins in the Knowledge Base page from official BIS sources.
- **Laboratories**: added individually or imported as CSV from the Laboratories page. Supported columns: `laboratory_name` (required), `address`, `city`, `state`, `contact_information`, `recognition_status`, `testing_capabilities`, `product_categories`, `official_source_url`, `last_verified_at`.

## API overview

All endpoints except register, login and health require `Authorization: Bearer <token>`. Admin-only endpoints are marked.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET/PATCH /api/auth/me`, `POST /api/auth/change-password` |
| Chat | `POST /api/chat/message`, `GET /api/chat/sessions`, `GET/PATCH/DELETE /api/chat/sessions/{id}`, `POST /api/chat/feedback` |
| Documents (admin) | `POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`, `PATCH /api/documents/{id}/status`, `POST /api/documents/{id}/reindex`, `DELETE /api/documents/{id}` |
| Standards | `GET /api/standards/search`, `POST /api/standards/compare`, `GET /api/standards/{id}` |
| Certification | `POST /api/certification/guidance`, `GET /api/certification/schemes`, `POST/PUT/DELETE /api/certification/schemes` (admin) |
| Laboratories | `GET /api/laboratories`, `GET /api/laboratories/filters`, `GET /api/laboratories/{id}`, `POST /api/laboratories` and `POST /api/laboratories/import` and `DELETE` (admin) |
| Hallmarking & consumer | `POST /api/hallmarking/query`, `POST /api/consumer/query`, `GET /api/consumer/resources` |
| Compliance | `POST /api/compliance/analyze` (multipart: `payload` JSON plus optional PDF, which is analysed but never indexed), `GET /api/compliance/reports` |
| Reports | `POST /api/reports/generate`, `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/download` (PDF), `DELETE /api/reports/{id}`, `GET /api/dashboard/summary` |
| Notifications | `GET /api/notifications`, `PATCH /api/notifications/{id}/read`, `POST /api/notifications/read-all`, `DELETE /api/notifications/{id}` |
| System | `GET /api/health` |

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

Tests run against a temporary SQLite database with in-process fakes for the LLM, the embedder and the Pinecone index, so they need no external services. The test fixture "IS 99999:2024" is clearly synthetic and is not real BIS data. To run the same tests against MySQL, set `TEST_DATABASE_URL`.

## Project layout

```
backend/
├── app/
│   ├── main.py              FastAPI app, middleware, error handlers, health
│   ├── config.py            Settings from environment variables
│   ├── api/routes/          HTTP endpoints
│   ├── agents/              Supervisor, specialist, translation and report agents
│   ├── graph/               LangGraph state, nodes, routing, workflow
│   ├── rag/                 PDF processing, OCR, chunking, embeddings, Pinecone, hybrid retrieval, ingestion
│   ├── services/            Auth, LLM, chat, standards, reports, labs, certification
│   ├── prompts/             Prompt templates for every agent
│   ├── database/            SQLAlchemy models, Pydantic schemas, CRUD
│   ├── utils/               Logging, errors, security helpers
│   └── tests/               Pytest suite
├── alembic/                 Database migrations
├── data/uploads/            Uploaded PDFs (git-ignored)
├── requirements.txt
└── .env.example
```

## Security notes

- No credentials are hard-coded; everything comes from `.env`, which is git-ignored.
- Passwords are hashed with bcrypt; JWT secrets shorter than 32 characters are rejected.
- Uploaded document text is treated as untrusted: injection patterns are neutralised and evidence is wrapped in delimiters before it reaches the LLM.
- Error responses never include stack traces.
