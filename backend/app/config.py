from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import secrets


load_dotenv()


class Settings(BaseModel):
    app_name: str = "BrunoFresh API"
    db_file: Path = Path(__file__).resolve().parent.parent / "data" / "database.db"
    images_dir: Path = Path(__file__).resolve().parent.parent / "data" / "images"
    hf_state_file: Path = Path(__file__).resolve().parent.parent / "data" / "hf_state.json"
    hf_email: str | None = os.getenv("HF_EMAIL")
    hf_password: str | None = os.getenv("HF_PASSWORD")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    )
    allowed_methods: tuple[str, ...] = tuple(
        method.strip().upper()
        for method in os.getenv("ALLOWED_METHODS", "GET,POST,PATCH,OPTIONS").split(",")
        if method.strip()
    )
    allowed_headers: tuple[str, ...] = tuple(
        header.strip()
        for header in os.getenv("ALLOWED_HEADERS", "Authorization,Content-Type").split(",")
        if header.strip()
    )
    scrape_concurrency_limit: int = int(os.getenv("SCRAPE_CONCURRENCY_LIMIT", "1"))
    app_passcode: str = os.getenv("APP_PASSCODE", "change-me-before-deploy")
    auth_secret: str = os.getenv("AUTH_SECRET", "local-dev-secret-do-not-use-in-prod-123456789")
    auth_token_ttl_minutes: int = int(os.getenv("AUTH_TOKEN_TTL_MINUTES", "10080"))
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "brunofresh_access_token")
    auth_cookie_secure: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    auth_cookie_samesite: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    categories: tuple[str, ...] = (
        "Produce",
        "Meat",
        "Fish",
        "Dairy",
        "Pantry",
        "Spices",
        "Bakery",
        "Frozen",
        "Beverages",
        "Condiments",
        "Other",
    )


settings = Settings()
settings.images_dir.mkdir(parents=True, exist_ok=True)
settings.hf_state_file.parent.mkdir(parents=True, exist_ok=True)
