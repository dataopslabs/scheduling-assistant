from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()["status"]=="ok"
def test_cases(): assert len(client.get("/api/cases").json())==10
def test_decide_blocks_unsafe():
    case=next(x for x in client.get("/api/cases").json() if x["case_id"]=="D-001")
    r=client.post("/api/decide",json=case); assert r.status_code==200
    assert r.json()["acceptable"] is False and r.json()["final_action"]=="escalate"
def test_eval(): 
    r=client.post("/api/evaluate").json()
    assert r["total"]==10 and r["passed"]==10
