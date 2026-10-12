"""Read-only access to the synthetic scenario fixtures."""
import json
from functools import lru_cache
from ..config import DATA_FILE
from ..schemas import SchedulingCase


@lru_cache
def _raw() -> list[dict]:
    return json.loads(DATA_FILE.read_text())


def list_cases() -> list[dict]:
    return _raw()


def get_case(case_id: str) -> SchedulingCase | None:
    return next((SchedulingCase.model_validate(c) for c in _raw() if c["case_id"] == case_id), None)
