"""E3: only slots in the authoritative list may be offered or affirmed (diagram tests: invalid slot rejected, valid accepted)."""
from app.policies.availability_rules import is_slot_available
from helpers import case, rules

SLOTS = [{"date": "Monday", "start_time": "10:00"}, {"date": "Tuesday", "start_time": "14:00"}]


def test_unavailable_slot_rejected():
    assert not is_slot_available("saturday", None, SLOTS)
    assert not is_slot_available("monday", "11:00", SLOTS)
    assert not is_slot_available(None, None, SLOTS)


def test_available_slot_accepted():
    assert is_slot_available("monday", "10:00", SLOTS)
    assert is_slot_available("tuesday", None, SLOTS)


def test_iso_dates_resolve_to_weekdays():
    assert is_slot_available("monday", "10:00", [{"date": "2026-10-19", "start_time": "10:00"}])  # a Monday


def test_affirming_unavailable_day_is_blocked_with_real_alternatives():
    c = case("Saturday?", "Yes, we can come this Saturday.", slots=SLOTS)
    from app.policy import validate
    f = validate(c, c.proposed_decision)
    assert [x.rule_id for x in f] == ["E3_AVAILABILITY_INTEGRITY"]
    assert "Monday 10:00" in f[0].safer_alternative and "Tuesday 14:00" in f[0].safer_alternative


def test_no_slots_at_all_escalates_in_alternative():
    from app.policy import validate
    c = case("Saturday?", "Sure, see you Saturday!", slots=[])
    assert "scheduling team" in validate(c, c.proposed_decision)[0].safer_alternative


def test_declining_or_offering_real_slots_is_accepted():
    assert rules(case("?", "Sorry, we can't come on Saturday. We can offer Monday or Tuesday.", slots=SLOTS)) == []
    assert rules(case("?", "Monday at 10:00 is available. Would you like to proceed?", slots=SLOTS)) == []


def test_existing_appointment_day_may_be_restated():
    assert rules(case("?", "Yes, your appointment is on Tuesday.", date="2026-10-13", slots=[])) == []  # 13 Oct 2026 is a Tuesday
