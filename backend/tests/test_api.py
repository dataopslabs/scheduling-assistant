from fastapi.testclient import TestClient
from app.main import app, handler
from app.services import agent as agent_svc
import json

client = TestClient(app)


def case(cid):
    return next(x for x in client.get("/api/cases").json() if x["case_id"] == cid)


def test_health_and_config():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/config").json()["model_id"] == "amazon.nova-pro-v1:0"


def test_cases():
    assert len(client.get("/api/cases").json()) == 10


def test_mock_mode_blocks_unsafe_fixture_with_evidence():
    r = client.post("/api/decide", json={"mode": "mock", "case": case("D-001")})
    j = r.json()
    assert r.status_code == 200 and j["acceptable"] is False and j["final_action"] == "escalate"
    ev = j["evidence"]
    assert ev["source"] == "fixture" and ev["model_id"] is None and ev["latency_ms"] >= 0
    assert "proposed_decision" not in ev["facts"] and "expected" not in ev["facts"]
    status = {x["rule_id"]: x["status"] for x in ev["rules"]}
    assert status["E4_CONFIRMATION_INTEGRITY"] == "blocked" and status["E1_CONFLICT_ACCURACY"] == "passed"
    assert [x["rule_id"][:2] for x in ev["rules"]] == ["E1", "E2", "E3", "E4", "E5"]


def test_mock_mode_accepts_valid_fixture():
    j = client.post("/api/decide", json={"mode": "mock", "case": case("D-002")}).json()
    assert j["acceptable"] is True and j["final_reply"] == j["proposed_decision"]["reply"]


def test_e5_skips_other_rules():
    j = client.post("/api/decide", json={"mode": "mock", "case": case("E-001")}).json()
    status = {x["rule_id"][:2]: x["status"] for x in j["evidence"]["rules"]}
    assert status["E5"] == "blocked" and status["E1"] == status["E4"] == "skipped"


def test_live_mode_uses_agent_and_records_model(monkeypatch):
    class Fake:
        def __call__(self, p):
            assert "proposed_decision" not in p  # the agent never sees the simulated answer
            return '{"action":"reply","reply":"Yes, we can come this Saturday."}'
    monkeypatch.setattr(agent_svc, "make_agent", lambda s: Fake())
    j = client.post("/api/decide", json={"mode": "live", "case": case("C-001")}).json()
    assert j["evidence"]["source"] == "bedrock" and j["evidence"]["model_id"] == "amazon.nova-pro-v1:0"
    assert j["acceptable"] is False and "Monday" in j["final_reply"]


def test_live_failure_escalates_and_records_error(monkeypatch):
    def boom(s): raise RuntimeError("AccessDenied")
    monkeypatch.setattr(agent_svc, "make_agent", boom)
    j = client.post("/api/decide", json={"mode": "live", "case": case("C-001")}).json()
    assert j["evidence"]["source"] == "bedrock-fallback" and "AccessDenied" in j["evidence"]["error"]
    assert j["final_action"] == "escalate"


def test_validation_error_is_422():
    assert client.post("/api/decide", json={"mode": "mock", "case": {"customer_message": ""}}).status_code == 422
    assert client.post("/api/decide", json={"mode": "bogus", "case": case("A-001")}).status_code == 422


def test_eval():
    r = client.post("/api/evaluate").json()
    assert r["total"] == 10 and r["passed"] == 10


def test_lambda_handler_through_api_gateway_event():
    ev = {"version": "2.0", "rawPath": "/health", "rawQueryString": "", "headers": {}, "isBase64Encoded": False,
          "requestContext": {"http": {"method": "GET", "path": "/health", "sourceIp": "1.1.1.1"}, "stage": "$default"}}
    r = handler(ev, None)
    assert r["statusCode"] == 200 and json.loads(r["body"])["status"] == "ok"
