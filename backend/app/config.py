from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os


load_dotenv()


class Settings(BaseModel):
    app_name: str = "BrunoFresh API"
    db_file: Path = Path(__file__).resolve().parent.parent / "database.db"
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
    scrape_concurrency_limit: int = int(os.getenv("SCRAPE_CONCURRENCY_LIMIT", "1"))
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
