"""Runtime configuration, read once from environment variables."""
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic_cases.json"
DATASETS_FILE = Path(__file__).resolve().parent.parent / "fixtures" / "datasets.json"


@dataclass(frozen=True)
class Settings:
    model_id: str = field(default_factory=lambda: os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
    region: str | None = field(default_factory=lambda: os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()))
    reviewer_model_id: str = field(default_factory=lambda: os.getenv("REVIEWER_MODEL_ID") or os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
    decider_model_id: str = field(default_factory=lambda: os.getenv("DECIDER_MODEL_ID") or os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
    writer_model_id: str = field(default_factory=lambda: os.getenv("WRITER_MODEL_ID") or os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
    decider_threshold: float = field(default_factory=lambda: float(os.getenv("DECIDER_THRESHOLD", "0.9")))   # below this -> human review
    review_claims: bool = field(default_factory=lambda: os.getenv("DECIDER_REVIEW_CLAIMS", "false").lower() == "true")  # extra LLM claim check
    writes_enabled: bool = field(default_factory=lambda: os.getenv("SCHEDULING_WRITES_ENABLED", "false").lower() == "true")  # demo: dry-run
    max_tokens: int = 500
    temperature: float = 0.0
    app_version: str = "0.4.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
