"""End-to-end guarded flow: reviewer -> decider -> python tools -> writer -> final guard (-> one rewrite -> safe response / human)."""
import json
from pathlib import Path
from app.agents.llm import AgentSet
from app.config import Settings
from app.schemas import DecideRequest, SchedulingCase
from app.services.scheduling_service import run_scheduling_flow
from conftest import FakeLLM

BASE = {c["case_id"]: c for c in json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_cases.json").read_text())}


def run(cid_or_dict, mode="mock", agents=None, settings=None, mutate=None):
    raw = dict(BASE[cid_or_dict]) if isinstance(cid_or_dict, str) else cid_or_dict
    if mutate: mutate(raw)
    return run_scheduling_flow(DecideRequest(mode=mode, case=SchedulingCase.model_validate(raw)), settings or Settings(), agents)


def steps(r): return [(s.key, s.status) for s in r.evidence.pipeline]


def test_valid_recorded_reply_is_approved_unchanged():
    r = run("D-002")
    assert r.resolution == "approved" and r.acceptable and r.final_reply == r.proposed_decision.reply
    assert steps(r) == [("request_reviewer", "ok"), ("decider", "ok"), ("python_tools", "ok"), ("response_writer", "ok"), ("final_guard", "ok")]


def test_unsafe_recorded_reply_gets_one_rewrite_from_the_evidence_pack():
    r = run("D-001")
    assert r.resolution == "rewritten" and not r.acceptable and r.evidence.rewrite_attempted
    assert r.proposed_decision.reply == "Yes, the crew will be there tomorrow."          # what the model said
    assert "not yet confirmed" in r.final_reply and "will be there" not in r.final_reply   # what the customer gets
    assert steps(r)[-2:] == [("final_guard", "blocked"), ("rewrite", "ok")]


def test_every_base_case_final_reply_passes_the_guard():
    from app.services.response_guard import validate_response
    for cid in BASE:
        r = run(cid)
        assert r.evidence.evidence_pack is not None
        assert validate_response(r.final_reply, r.evidence.evidence_pack).acceptable or r.resolution == "safe_response", cid


def test_failed_rewrite_falls_back_to_fixed_safe_response(fake_llm):
    # live writer keeps promising the crew: first draft and rewrite both fail -> fixed safe response
    f = fake_llm(reviewer={"intent": "crew_attendance", "asks_crew_attendance": True, "summary": "x"},
                 decider={"next_action": "answer_status", "confidence": 0.97, "reason": "r"},
                 writer={"action": "reply", "reply": "Yes, the crew will be there tomorrow."})
    r = run("D-001", mode="live")
    assert r.resolution == "safe_response" and r.final_action == "escalate" and "will be there" not in r.final_reply
    assert len(f["writer"].prompts) == 2 and "REJECTED" in f["writer"].prompts[1]          # exactly one rewrite attempt
    assert r.evidence.source == "bedrock" and r.evidence.model_id == "amazon.nova-pro-v1:0"


def test_live_rewrite_can_succeed(fake_llm):
    f = fake_llm(reviewer={"intent": "crew_attendance", "asks_crew_attendance": True, "summary": "x"},
                 decider={"next_action": "answer_status", "confidence": 0.97, "reason": "r"},
                 writer=[{"action": "reply", "reply": "Yes, the crew will be there tomorrow."},
                         {"action": "escalate", "reply": "The appointment is tentative and crew attendance is not yet confirmed. We will update you."}])
    r = run("D-001", mode="live")
    assert r.resolution == "rewritten" and r.final_action == "escalate" and "not yet confirmed" in r.final_reply
    assert len(f["writer"].prompts) == 2


def test_low_decider_confidence_routes_to_a_human_and_skips_the_writer(fake_llm):
    f = fake_llm(decider={"next_action": "offer_slots", "confidence": 0.62, "reason": "unsure"})
    r = run("C-001", mode="live")
    assert r.resolution == "human_escalation" and r.final_action == "escalate"
    assert f["writer"].prompts == []
    assert ("response_writer", "skipped") in steps(r)


def test_threshold_is_configurable_and_inclusive(fake_llm):
    fake_llm(decider={"next_action": "offer_slots", "confidence": 0.9, "reason": "r"},
             writer={"action": "reply", "reply": "Sorry, we don't have Saturday availability. We can offer: Monday 10:00 or Tuesday 14:00."})
    assert run("C-001", mode="live").resolution == "approved"                          # 0.9 >= 0.9
    assert run("C-001", mode="live", settings=Settings(decider_threshold=0.95)).resolution == "human_escalation"


def test_unclear_message_in_mock_mode_goes_to_a_human():
    r = run("C-001", mutate=lambda d: d.update(customer_message="asdf qwer", proposed_decision=None))
    assert r.resolution == "human_escalation" and r.evidence.judgment.confidence < 0.9


def test_agent_failures_degrade_to_human_never_raw_text(fake_llm):
    fake_llm(reviewer=RuntimeError("AccessDenied"))
    r = run("C-001", mode="live")
    assert r.resolution == "human_escalation" and r.evidence.source == "bedrock-fallback" and "AccessDenied" in r.evidence.error
    fake_llm(writer="not json")
    r = run("C-001", mode="live")
    assert r.resolution == "human_escalation" and r.evidence.error


def test_agents_never_see_expected_outcome_recorded_reply_or_ids(fake_llm):
    f = fake_llm()
    run("D-001", mode="live")
    seen = " ".join(p for fk in f.values() for p in fk.prompts)
    for secret in ("expected", "proposed_decision", "Yes, the crew will be there", "E4_CONFIRMATION", "D-001"):
        assert secret not in seen, secret


def test_booking_needs_agreement_to_an_available_slot_and_is_dry_run_by_default():
    raw = {"customer_message": "Yes, please book Monday at 10:00", "appointment": {"status": "none"}, "crew": {"confirmation_status": "unknown"},
           "available_slots": [{"date": "Monday", "start_time": "10:00"}]}
    r = run(raw)
    pack = r.evidence.evidence_pack
    assert r.evidence.draft_request.confirms_slot and pack.booking and pack.booking.dry_run and not pack.booking.performed
    assert "now booked" not in r.final_reply.lower()
    assert "team will confirm" in r.final_reply
    # writes enabled: a booking is performed and may be stated
    r2 = run(raw, settings=Settings(writes_enabled=True))
    assert r2.evidence.evidence_pack.booking.performed and "is now booked" in r2.final_reply and r2.resolution == "approved"


def test_no_booking_without_a_matching_available_slot():
    raw = {"customer_message": "Yes, please book Saturday at 10:00", "appointment": {"status": "none"}, "crew": {"confirmation_status": "unknown"},
           "available_slots": [{"date": "Monday", "start_time": "10:00"}]}
    r = run(raw)
    assert r.evidence.evidence_pack.booking is None and "Saturday" in r.final_reply and "Monday 10:00" in r.final_reply


def test_evidence_contains_pipeline_pack_judgment_and_rules():
    r = run("C-001")
    ev = r.evidence
    assert [s.key for s in ev.pipeline][:3] == ["request_reviewer", "decider", "python_tools"]
    assert ev.draft_request.intent == "availability_check" and ev.judgment.next_action == "offer_slots"
    assert [s.label for s in ev.evidence_pack.available_slots] == ["Monday 10:00", "Tuesday 14:00"]
    assert [x.rule_id[:2] for x in ev.rules] == ["E1", "E2", "E3", "E4", "E5"]


def test_llm_claiming_slot_agreement_cannot_trigger_a_booking(fake_llm):
    """Python verifies agreement on the raw message; the reviewer's confirms_slot flag alone never authorises a write."""
    fake_llm(reviewer={"intent": "booking_request", "requested_day": "monday", "requested_time": "10:00", "confirms_slot": True, "summary": "x"},
             decider={"next_action": "book_slot", "confidence": 0.99, "reason": "r"},
             writer={"action": "reply", "reply": "Monday 10:00 is available. Would you like to proceed?"})
    raw = {"customer_message": "Can you come Monday at 10:00?", "appointment": {"status": "none"}, "crew": {"confirmation_status": "unknown"},
           "available_slots": [{"date": "Monday", "start_time": "10:00"}]}
    r = run(raw, mode="live", settings=Settings(writes_enabled=True))
    assert r.evidence.evidence_pack.booking is None


def test_deferral_safe_response_waits_instead_of_offering_slots(fake_llm):
    """Both E2 (pushing) and E3 (affirming an unavailable day) fire; the customer deferred, so the safe reply must be 'wait'."""
    fake_llm(reviewer={"intent": "defer_to_customer", "customer_will_followup": True, "requested_day": "monday", "summary": "x"},
             decider={"next_action": "wait_for_customer", "confidence": 0.97, "reason": "r"},
             writer={"action": "reply", "reply": "Sure, we can come Monday. Shall we book it?"})
    raw = {"customer_message": "I'm out of town this week, I will get back to you next Monday.", "appointment": {"status": "none"},
           "crew": {"confirmation_status": "unknown"}, "available_slots": [{"date": "Wednesday", "start_time": "10:00"}]}
    r = run(raw, mode="live")
    assert {f.rule_id for f in r.findings} >= {"E2_CUSTOMER_INTENT", "E3_AVAILABILITY_INTEGRITY"}
    assert r.resolution == "safe_response" and r.final_action == "wait"
    assert "message us when you are back" in r.final_reply and "Wednesday" not in r.final_reply


def test_safe_response_uses_highest_precedence_finding_from_either_draft(fake_llm):
    # first draft breaks E4 (crew promise); the rewrite breaks only E3. E4 outranks E3, so its alternative is used.
    fake_llm(reviewer={"intent": "crew_attendance", "asks_crew_attendance": True, "summary": "x"},
             decider={"next_action": "answer_status", "confidence": 0.97, "reason": "r"},
             writer=[{"action": "reply", "reply": "Yes, the crew will be there tomorrow."},
                     {"action": "reply", "reply": "Sure, we can come Saturday."}])
    r = run("D-001", mode="live")
    assert r.resolution == "safe_response" and "not yet fully confirmed" in r.final_reply


def test_human_escalation_is_not_reported_as_an_approved_draft():
    r = run("C-001", mutate=lambda d: d.update(customer_message="asdf qwer", proposed_decision=None))
    assert r.resolution == "human_escalation" and r.acceptable is False
