import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.policy import validate
from app.schemas import SchedulingCase

RAW = json.loads((Path(__file__).resolve().parents[1] / "data" / "datasets.json").read_text())
client = TestClient(app)


def test_at_least_three_datasets_for_each_of_the_ten_use_cases():
    base = {c["case_id"] for c in json.loads((Path(__file__).resolve().parents[1] / "data" / "cases.json").read_text())}
    assert len(base) == 10
    per = {}
    for d in RAW:
        per[d["use_case"]] = per.get(d["use_case"], 0) + 1
    assert set(per) == base and min(per.values()) >= 3 and len(RAW) >= 30
    assert len({d["case_id"] for d in RAW}) == len(RAW)


@pytest.mark.parametrize("raw", RAW, ids=[d["case_id"] for d in RAW])
def test_dataset_policy_outcome_matches_expectation(raw):
    c = SchedulingCase.model_validate(raw)
    rules = [f.rule_id for f in validate(c, c.proposed_decision)]
    assert (not rules) == raw["expected"]["acceptable"], (raw["title"], rules)
    if raw["expected"]["rule"]:
        assert raw["expected"]["rule"] in rules


def test_datasets_endpoint_and_filter():
    assert len(client.get("/api/datasets").json()) == len(RAW)
    assert {d["use_case"] for d in client.get("/api/datasets", params={"use_case": "C-001"}).json()} == {"C-001"}


def test_batch_mock_matches_expectations():
    j = client.post("/api/batch", json={"mode": "mock", "use_case": "D-001"}).json()
    assert j["total"] == 3 and j["blocked"] == 3 and all(i["expected_acceptable"] is False for i in j["items"])


def test_batch_limits():
    assert client.post("/api/batch", json={"mode": "mock", "use_case": "ZZ"}).status_code == 404
    assert client.post("/api/batch", json={"mode": "mock", "case_ids": [d["case_id"] for d in RAW[:11]]}).status_code == 422


def test_agent_never_sees_expected_or_proposed_or_ids(monkeypatch):
    from app.services import agent as agent_svc
    seen = []
    class Fake:
        def __call__(self, p): seen.append(p); return '{"action":"reply","reply":"ok"}'
    monkeypatch.setattr(agent_svc, "make_agent", lambda s: Fake())
    client.post("/api/batch", json={"mode": "live", "use_case": "B-001"})
    assert len(seen) == 3 and all(w not in p for p in seen for w in ("expected", "proposed_decision", "use_case", "E2_CUSTOMER"))
