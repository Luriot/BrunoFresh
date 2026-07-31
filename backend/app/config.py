from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import secrets


load_dotenv()


PRODUCTION_ENVIRONMENTS = {"prod", "production"}
_MIN_SECRET_LEN = 32


def _resolve_auth_secret(environment: str) -> str:
    """Resolve the access-token signing secret with no committed default.

    AUTH_SECRET env var always wins. In production, missing/short secret is a
    hard error. In dev/test, a random per-process ephemeral secret is generated so
    no publicly-known value ever signs tokens — set AUTH_SECRET explicitly if
    you need sessions to survive process restarts.
    """
    val = os.getenv("AUTH_SECRET")
    if val:
        return val.strip()
    if environment in PRODUCTION_ENVIRONMENTS:
        raise RuntimeError("AUTH_SECRET must be set in production (>= 32 chars, high entropy)")
    return secrets.token_urlsafe(48)


def _resolve_session_secret(environment: str, auth_secret: str) -> str:
    """Resolve the session-cookie signing secret.

    SESSION_SECRET env var wins; otherwise falls back to AUTH_SECRET. Never falls
    back to a hardcoded literal. In production, an unset SESSION_SECRET that
    also has no AUTH_SECRET is rejected upstream by _resolve_auth_secret.
    """
    val = os.getenv("SESSION_SECRET")
    if val and val.strip():
        return val.strip()
    return auth_secret


class Settings(BaseModel):
    app_name: str = "BrunoFresh API"
    environment: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
    db_file: Path = Path(__file__).resolve().parent.parent / "data" / "database.db"
    images_dir: Path = Path(__file__).resolve().parent.parent / "data" / "images"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
    ollama_num_predict: int = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    )
    allowed_methods: tuple[str, ...] = tuple(
        method.strip().upper()
        for method in os.getenv("ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS").split(",")
        if method.strip()
    )
    allowed_headers: tuple[str, ...] = tuple(
        header.strip()
        for header in os.getenv("ALLOWED_HEADERS", "Authorization,Content-Type").split(",")
        if header.strip()
    )
    scrape_concurrency_limit: int = int(os.getenv("SCRAPE_CONCURRENCY_LIMIT", "1"))
    auth_secret: str = ""
    session_secret: str = ""
    auth_token_ttl_minutes: int = int(os.getenv("AUTH_TOKEN_TTL_MINUTES", "10080"))  # 7 days default
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "brunofresh_access_token")
    auth_cookie_secure: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    auth_cookie_samesite: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    # DB admin interface (/dbadmin). Defaults to enabled in development, disabled
    # in production. Set DBADMIN_ENABLED=true to explicitly enable it in prod
    # (e.g. when accessed exclusively via an SSH tunnel).
    dbadmin_enabled: bool = os.getenv(
        "DBADMIN_ENABLED",
        "false" if os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
                   in PRODUCTION_ENVIRONMENTS else "true",
    ).lower() == "true"
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

    if len(current.auth_secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"AUTH_SECRET must contain at least {_MIN_SECRET_LEN} characters of high entropy"
        )
    if len(current.session_secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"SESSION_SECRET must contain at least {_MIN_SECRET_LEN} characters of high entropy"
        )

    if current.auth_token_ttl_minutes <= 0:
        raise ValueError("AUTH_TOKEN_TTL_MINUTES must be a positive integer")

    in_production = current.environment in PRODUCTION_ENVIRONMENTS

    if in_production and not current.auth_cookie_secure:
        raise RuntimeError("AUTH_COOKIE_SECURE must be true in production")

    if in_production and current.dbadmin_enabled:
        raise RuntimeError(
            "DBADMIN_ENABLED=true in production is not allowed: the /dbadmin interface would be "
            "publicly reachable. Restrict access at the network level or disable it."
        )


settings = Settings()
settings.auth_secret = _resolve_auth_secret(settings.environment)
settings.session_secret = _resolve_session_secret(settings.environment, settings.auth_secret)
_validate_security_settings(settings)
settings.images_dir.mkdir(parents=True, exist_ok=True)