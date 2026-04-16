from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os


load_dotenv()


class Settings(BaseModel):
    app_name: str = "MealCart API"
    db_file: Path = Path(__file__).resolve().parent.parent / "database.db"
    images_dir: Path = Path(__file__).resolve().parent.parent / "data" / "images"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


settings = Settings()
settings.images_dir.mkdir(parents=True, exist_ok=True)
