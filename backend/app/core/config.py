from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

class Settings(BaseSettings):
    """Application settings."""
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LearnMate"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'study_sessions.db'}")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "learnmate")
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Runtime paths
    DATA_DIR: str = os.getenv("LEARNMATE_DATA_DIR", str(PROJECT_ROOT / "data"))
    JOB_REQUEST_DIR: str = os.getenv("LEARNMATE_JOB_REQUEST_DIR", str(Path(DATA_DIR) / "chat_requests"))
    METRICS_PATH: str = os.getenv("LEARNMATE_METRICS_PATH", str(Path(DATA_DIR) / "metrics" / "processing_metrics.jsonl"))

    # File Upload Configuration
    UPLOAD_DIR: str = os.getenv("LEARNMATE_UPLOAD_DIR", str(PROJECT_ROOT / "uploads"))
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Frontend/CORS Configuration
    BACKEND_CORS_ORIGINS: str = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001",
    )

    # Local model runtime
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:8b")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
