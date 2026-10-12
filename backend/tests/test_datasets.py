import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.policy import validate
from app.schemas import SchedulingCase

RAW = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "datasets.json").read_text())
client = TestClient(app)


def test_at_least_three_datasets_for_each_of_the_ten_use_cases():
    base = {c["case_id"] for c in json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_cases.json").read_text())}
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


def test_every_dataset_flows_through_the_pipeline_and_the_final_reply_is_safe():
    from app.schemas import EvidencePack
    from app.services.response_guard import validate_response
    for d in RAW:
        j = client.post("/api/decide", json={"mode": "mock", "case": d}).json()
        assert j["resolution"] != "human_escalation", (d["case_id"], j["evidence"]["judgment"])       # reviewer/decider are confident on all 30
        assert (j["resolution"] == "approved") == d["expected"]["acceptable"], d["case_id"]            # unsafe recorded replies are never approved
        pack = EvidencePack.model_validate(j["evidence"]["evidence_pack"])
        if j["resolution"] != "safe_response":                                                         # approved or rewritten replies re-validate cleanly
            assert validate_response(j["final_reply"], pack).acceptable, d["case_id"]


def test_batch_agents_never_see_expected_or_recorded_reply_or_ids(fake_llm):
    f = fake_llm(reviewer={"intent": "defer_to_customer", "customer_will_followup": True, "summary": "x"},
                 decider={"next_action": "wait_for_customer", "confidence": 0.96, "reason": "r"},
                 writer={"action": "wait", "reply": "Thanks for letting us know. Please message us when you are back."})
    client.post("/api/batch", json={"mode": "live", "use_case": "B-001"})
    seen = " ".join(p for fk in f.values() for p in fk.prompts)
    assert len(f["writer"].prompts) == 3 and all(w not in seen for w in ("expected", "proposed_decision", "use_case", "E2_CUSTOMER", "B-001"))
