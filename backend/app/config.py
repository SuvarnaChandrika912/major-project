from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Root .env is the single source of truth; backend/.env can override locally.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "BIS SAATHI"
    LOG_LEVEL: str = "INFO"

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "bis_saathi"
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""
    # Optional full override, e.g. for tests: sqlite:///./test.db
    DATABASE_URL: str = ""

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "bis-saathi"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_NAMESPACE: str = "bis-documents"

    # LLM (groq | ollama)
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 120
    AGENT_TIMEOUT_SECONDS: int = 180

    # Embeddings / retrieval
    EMBEDDING_MODEL: str = "llama-text-embed-v2"
    EMBEDDING_DIMENSION: int = 1024
    RERANKER_MODEL: str = ""
    RETRIEVAL_TOP_K: int = 8

    # OCR
    TESSERACT_CMD: str = ""
    OCR_LANGUAGES: str = "eng"

    # Auth
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_EMAILS: str = ""

    # Uploads
    MAX_UPLOAD_MB: int = 50
    UPLOAD_DIR: str = str(BACKEND_DIR / "data" / "uploads")
    PROCESSED_DIR: str = str(BACKEND_DIR / "data" / "processed")

    # Optional Redis cache
    REDIS_URL: str = ""

    FRONTEND_URL: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/"
            f"{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    @property
    def pinecone_configured(self) -> bool:
        return bool(self.PINECONE_API_KEY and self.PINECONE_INDEX_NAME)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
