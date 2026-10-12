import json
import pytest
from app.schemas import SchedulingCase, ProposedDecision
from app.policy import validate


def case(msg, reply, status="confirmed", crew="confirmed", slots=None, jobs=None, date="2026-10-13"):
    return SchedulingCase.model_validate({
        "customer_message": msg, "appointment": {"date": date, "status": status},
        "crew": {"confirmation_status": crew}, "available_slots": slots or [], "other_jobs": jobs or [],
        "proposed_decision": {"action": "reply", "reply": reply}})


def rules(c):
    return [f.rule_id for f in validate(c, c.proposed_decision)]


def test_any_weekday_without_slot_is_blocked():
    c = case("Friday?", "Sure, we can come Friday.", slots=[{"date": "Monday", "start_time": "10:00"}])
    assert rules(c) == ["E3_AVAILABILITY_INTEGRITY"]


def test_iso_date_slot_resolves_to_weekday():
    c = case("Monday?", "Yes, we can come Monday.", slots=[{"date": "2026-10-19", "start_time": "10:00"}])  # a Monday
    assert rules(c) == []


def test_declining_a_day_is_not_a_commitment():
    assert rules(case("Sat?", "Sorry, we can't come on Saturday.", slots=[{"day": "Monday"}])) == []


def test_attendance_promise_variants_blocked_when_crew_unknown():
    for reply in ("Yes, the crew is coming tomorrow.", "Our team will arrive at 9.", "We'll be there tomorrow."):
        assert "E4_CONFIRMATION_INTEGRITY" in rules(case("?", reply, status="tentative", crew="unknown")), reply


def test_confirmed_wording_blocked_when_status_tentative():
    assert "E4_CONFIRMATION_INTEGRITY" in rules(case("?", "Your appointment is confirmed.", status="tentative", crew="unknown"))


def test_attendance_promise_ok_when_crew_confirmed():
    assert rules(case("?", "Yes, the crew will be there tomorrow.")) == []


def test_conflict_claim_without_active_job_is_blocked_but_real_conflict_allowed():
    assert rules(case("?", "There is a conflict.", jobs=[{"status": "completed"}])) == ["E1_CONFLICT_ACCURACY"]
    assert rules(case("?", "There is a conflict.", jobs=[{"status": "in_progress"}])) == []


def test_deferral_ack_with_neutral_scheduling_word_is_accepted():
    msg = "I'm away. I'll let you know when I'm back."
    assert rules(case(msg, "Understood, message us when you're back so we can schedule your appointment.", status="none", crew="unknown")) == []
    assert rules(case(msg, "How about tomorrow morning?", status="none", crew="unknown")) == ["E2_CUSTOMER_INTENT"]
