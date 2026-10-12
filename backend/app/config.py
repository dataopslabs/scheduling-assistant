"""Runtime configuration, read once from environment variables."""
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "cases.json"
DATASETS_FILE = Path(__file__).resolve().parent.parent / "data" / "datasets.json"


@dataclass(frozen=True)
class Settings:
    model_id: str = field(default_factory=lambda: os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
    region: str | None = field(default_factory=lambda: os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()))
    max_tokens: int = 500
    temperature: float = 0.0
    app_version: str = "0.3.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
