from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import warnings


load_dotenv()


DEFAULT_APP_PASSCODE = "change-me-before-deploy"
DEFAULT_AUTH_SECRET = "local-dev-secret-do-not-use-in-prod-123456789"
PRODUCTION_ENVIRONMENTS = {"prod", "production"}


class Settings(BaseModel):
    app_name: str = "BrunoFresh API"
    environment: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
    db_file: Path = Path(__file__).resolve().parent.parent / "data" / "database.db"
    images_dir: Path = Path(__file__).resolve().parent.parent / "data" / "images"
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
    app_passcode: str = os.getenv("APP_PASSCODE", DEFAULT_APP_PASSCODE)
    auth_secret: str = os.getenv("AUTH_SECRET", DEFAULT_AUTH_SECRET)
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


def _validate_security_settings(current: Settings) -> None:
    valid_samesite = {"lax", "strict", "none"}
    if current.auth_cookie_samesite not in valid_samesite:
        raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none")

    if len(current.auth_secret) < 32:
        raise ValueError("AUTH_SECRET must contain at least 32 characters")

    in_production = current.environment in PRODUCTION_ENVIRONMENTS

    if in_production and current.app_passcode == DEFAULT_APP_PASSCODE:
        raise RuntimeError("APP_PASSCODE cannot use the default value in production")

    if in_production and current.auth_secret == DEFAULT_AUTH_SECRET:
        raise RuntimeError("AUTH_SECRET cannot use the default value in production")

    if in_production and not current.auth_cookie_secure:
        raise RuntimeError("AUTH_COOKIE_SECURE must be true in production")

    if not in_production and current.app_passcode == DEFAULT_APP_PASSCODE:
        warnings.warn(
            "Using default APP_PASSCODE in development. Set APP_PASSCODE in your environment.",
            stacklevel=2,
        )


settings = Settings()
_validate_security_settings(settings)
settings.images_dir.mkdir(parents=True, exist_ok=True)
