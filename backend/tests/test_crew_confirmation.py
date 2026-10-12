"""E4: unknown/tentative crew status can never become a promise; booking claims need a performed booking."""
from helpers import case, rules


def unknown(reply, status="tentative", crew="unknown"): return case("Is the crew coming?", reply, status=status, crew=crew)


def test_attendance_promises_blocked_when_crew_unconfirmed():
    for reply in ("Yes, the crew will be there tomorrow.", "The crew is coming tomorrow.", "Our team will arrive at 9.", "We'll be there tomorrow.", "You can count on us."):
        assert "E4_CONFIRMATION_INTEGRITY" in rules(unknown(reply)), reply


def test_confirmed_wording_blocked_when_status_not_confirmed():
    assert "E4_CONFIRMATION_INTEGRITY" in rules(unknown("Your appointment is confirmed."))


def test_honest_uncertainty_accepted():
    assert rules(unknown("Your appointment is tentative and crew attendance is not yet confirmed.")) == []
    assert rules(unknown("We'll check and update you once the crew is confirmed.")) == []


def test_confirmed_crew_may_be_promised():
    assert rules(unknown("Yes, the crew will be there tomorrow.", status="confirmed", crew="confirmed")) == []


def test_booking_claim_without_performed_booking_is_blocked():
    assert "E4_CONFIRMATION_INTEGRITY" in rules(unknown("Great, you're booked for Monday at 10:00.", status="none", crew="unknown"))


def test_missing_data_fails_closed_e5():
    assert rules(case("?", "Yes, everything is confirmed.", status="", crew="")) == ["E5_DATA_UNCERTAINTY"]
