"""Agents: request reviewer, decider (typed judgment, confidence), response writer, and the Strands/Bedrock wiring."""
import json
from pathlib import Path
import pytest
from app.agents import decider_client, request_reviewer, response_writer
from app.agents.llm import AgentSet, make_agent
from app.config import Settings
from app.schemas import DraftRequest, EvidencePack, Judgment, AppointmentRecord, SlotRecord
from conftest import FakeLLM

DATASETS = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "datasets.json").read_text())
BASE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_cases.json").read_text())
EXPECTED_INTENT = {"A": "status_check", "B": "defer_to_customer", "C": "availability_check", "D": "crew_attendance", "E": "status_check"}


@pytest.mark.parametrize("raw", BASE + DATASETS, ids=[c["case_id"] for c in BASE + DATASETS])
def test_heuristic_reviewer_gets_every_synthetic_message_right(raw):
    uc = raw.get("use_case") or raw["case_id"]
    got = request_reviewer.heuristic_extract(raw["customer_message"])
    want = EXPECTED_INTENT[uc[0]]
    # A-001.2 / D-style messages about the crew coming are attendance questions; both route to answer_status
    ok = {got.intent} <= {want, "crew_attendance"} if want == "status_check" else got.intent == want
    assert ok, (raw["customer_message"], got.intent)


def test_reviewer_extracts_day_time_and_followup():
    d = request_reviewer.heuristic_extract("Can you come Monday at 10:00?")
    assert (d.intent, d.requested_day, d.requested_time) == ("availability_check", "monday", "10:00")
    assert request_reviewer.heuristic_extract("I'll let you know when I'm back").customer_will_followup


def test_reviewer_detects_slot_agreement():
    d = request_reviewer.heuristic_extract("Yes, please book Monday at 10:00")
    assert d.intent == "booking_request" and d.confirms_slot


def test_decider_confidence_gate_inputs():
    assert decider_client.heuristic_decide(DraftRequest(intent="availability_check")).confidence >= 0.9
    assert decider_client.heuristic_decide(DraftRequest(intent="other")).confidence < 0.9
    assert decider_client.heuristic_decide(DraftRequest(intent="status_check", customer_will_followup=True)).next_action == "wait_for_customer"


def test_live_agents_return_typed_output_and_see_only_their_inputs():
    s = Settings()
    rev = FakeLLM({"intent": "availability_check", "requested_day": "saturday", "summary": "s"})
    dec = FakeLLM({"next_action": "offer_slots", "confidence": 0.93, "reason": "r"})
    agents = AgentSet(reviewer=rev, decider=dec)
    draft = request_reviewer.extract_request("Can you come Saturday?", True, s, agents)
    j = decider_client.decide(draft, "Can you come Saturday?", True, s, agents)
    assert isinstance(draft, DraftRequest) and isinstance(j, Judgment) and j.confidence == 0.93
    assert "slots" not in rev.prompts[0] and "appointment" not in dec.prompts[0]      # no scheduling facts leak to these agents


def test_invalid_typed_output_raises():
    s = Settings()
    with pytest.raises(Exception):
        decider_client.decide(DraftRequest(), "x", True, s, AgentSet(decider=FakeLLM({"next_action": "book_everything", "confidence": 2})))


def test_writer_sees_only_the_evidence_pack_and_violations_on_rewrite():
    s = Settings()
    pack = EvidencePack(customer_message="Is the crew coming?", appointment=AppointmentRecord(status="tentative"), crew_confirmation="unknown")
    w = FakeLLM({"action": "reply", "reply": "ok"})
    response_writer.write(pack, Judgment(next_action="answer_status", confidence=0.95), DraftRequest(), True, s, AgentSet(writer=w))
    from app.schemas import PolicyFinding
    response_writer.write(pack, Judgment(next_action="answer_status", confidence=0.95), DraftRequest(), True, s, AgentSet(writer=w),
                          violations=[PolicyFinding(rule_id="E4", reason="promised the crew", safer_alternative="x")])
    assert "Evidence pack" in w.prompts[0] and "REJECTED" not in w.prompts[0] and "REJECTED" in w.prompts[1] and "promised the crew" in w.prompts[1]


def test_template_writer_never_over_promises():
    j, d = Judgment(next_action="answer_status", confidence=0.95), DraftRequest(asks_crew_attendance=True)
    p = EvidencePack(customer_message="?", appointment=AppointmentRecord(status="tentative", date="2026-10-13"), crew_confirmation="unknown")
    out = response_writer.template_write(p, j, d)
    assert "not yet confirmed" in out.reply and out.action == "escalate"
    p2 = EvidencePack(customer_message="?", data_complete=False, missing=["crew"])
    assert response_writer.template_write(p2, j, d).action == "escalate"


def test_make_agent_maps_model_id_and_attaches_no_tools(monkeypatch):
    seen = {}
    import strands, strands.models
    monkeypatch.setattr(strands.models, "BedrockModel", lambda **kw: seen.update(kw) or object())
    monkeypatch.setattr(strands, "Agent", lambda **kw: seen.update(kw) or "agent")
    make_agent("my-model-id", "SYS", Settings())
    assert seen["model_id"] == "my-model-id" and seen["temperature"] == 0.0 and seen["system_prompt"] == "SYS" and "tools" not in seen


def test_per_role_model_ids_default_to_the_main_model(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "m-main"); monkeypatch.setenv("DECIDER_MODEL_ID", "m-decider")
    monkeypatch.delenv("REVIEWER_MODEL_ID", raising=False); monkeypatch.delenv("WRITER_MODEL_ID", raising=False)
    s = Settings()
    assert (s.reviewer_model_id, s.decider_model_id, s.writer_model_id) == ("m-main", "m-decider", "m-main")


def test_unknown_intent_labels_are_coerced_not_fatal():
    assert DraftRequest.model_validate({"intent": "asks_crew_attendance"}).intent == "crew_attendance"
    assert DraftRequest.model_validate({"intent": "confirm_slot"}).intent == "booking_request"
    assert DraftRequest.model_validate({"intent": "something_new"}).intent == "other"
    assert DraftRequest.model_validate({}).intent == "other"
