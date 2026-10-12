import json
from pathlib import Path
import pytest
from app.schemas import SchedulingCase
from app.policy import validate
CASES=json.loads((Path(__file__).resolve().parents[1]/"fixtures"/"synthetic_cases.json").read_text())
@pytest.mark.parametrize("raw",CASES,ids=[x["case_id"] for x in CASES])
def test_expected_policy_result(raw):
    c=SchedulingCase.model_validate(raw)
    assert (not validate(c,c.proposed_decision))==raw["expected"]["acceptable"], raw["case_id"]
def test_crew_promise_blocked():
    c=SchedulingCase.model_validate(next(x for x in CASES if x["case_id"]=="D-001"))
    assert "E4_CONFIRMATION_INTEGRITY" in [f.rule_id for f in validate(c,c.proposed_decision)]
def test_safe_uncertainty_accepted():
    c=SchedulingCase.model_validate(next(x for x in CASES if x["case_id"]=="D-002"))
    assert validate(c,c.proposed_decision)==[]
def test_missing_data_fails_closed():
    c=SchedulingCase.model_validate(next(x for x in CASES if x["case_id"]=="E-001"))
    assert "E5_DATA_UNCERTAINTY" in [f.rule_id for f in validate(c,c.proposed_decision)]
