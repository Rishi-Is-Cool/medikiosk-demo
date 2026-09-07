import os
from pathlib import Path
from typing import List, Optional, Set
from dotenv import load_dotenv

# Load .env file from root or ml_backend directory
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

dotenv_path = BASE_DIR / ".env"
if not dotenv_path.exists():
    dotenv_path = PROJECT_ROOT / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()


class Settings:
    # Service settings
    APP_NAME: str = "MediKiosk AI/ML Intelligence Service"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Security & CORS Settings
    _default_cors = "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8000"
    CORS_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", _default_cors).split(",") if origin.strip()
    ]

    # Document Upload Constraints
    ALLOWED_MIME_TYPES: Set[str] = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/tiff",
        "image/heic",
        "application/pdf",
    }
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))  # 20 MB

    # LLM Settings (Updated default model: gemini-3.6-flash matching repo baseline)
    VISION_LLM_PROVIDER: str = os.getenv("VISION_LLM_PROVIDER", "gemini").lower()
    VISION_LLM_API_KEY: Optional[str] = (
        os.getenv("VISION_LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    VISION_LLM_MODEL: str = os.getenv("VISION_LLM_MODEL", "gemini-3.6-flash")

    TEXT_LLM_PROVIDER: str = os.getenv(
        "TEXT_LLM_PROVIDER", os.getenv("VISION_LLM_PROVIDER", "gemini")
    ).lower()
    TEXT_LLM_API_KEY: Optional[str] = (
        os.getenv("TEXT_LLM_API_KEY")
        or os.getenv("VISION_LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    TEXT_LLM_MODEL: str = os.getenv("TEXT_LLM_MODEL", "gemini-3.6-flash")

    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "sample_documents"
    NORMALIZATION_DICT_PATH: Path = DATA_DIR / "normalization_dictionary.json"
    LAB_REFERENCE_PATH: Path = DATA_DIR / "lab_reference_ranges.json"


settings = Settings()
