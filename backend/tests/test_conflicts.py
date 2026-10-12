"""E1: completed or cancelled jobs are not active conflicts."""
from helpers import case, rules


def test_completed_job_is_not_a_conflict():
    assert rules(case("?", "There is a scheduling conflict.", jobs=[{"status": "completed"}])) == ["E1_CONFLICT_ACCURACY"]


def test_cancelled_job_is_not_a_conflict():
    assert rules(case("?", "There is a crew conflict.", jobs=[{"status": "cancelled"}])) == ["E1_CONFLICT_ACCURACY"]


def test_active_job_supports_a_conflict_claim():
    assert rules(case("?", "There is a conflict.", jobs=[{"status": "in_progress"}])) == []


def test_unfortunately_does_not_hide_a_conflict_claim():
    assert rules(case("?", "Unfortunately there is a crew conflict.", jobs=[{"status": "completed"}])) == ["E1_CONFLICT_ACCURACY"]


def test_denying_a_conflict_is_fine():
    assert rules(case("?", "There is no scheduling conflict.", jobs=[{"status": "completed"}])) == []


def test_confirming_without_conflict_wording_is_fine():
    assert rules(case("?", "Your installation is confirmed for 09:00-12:00.", jobs=[{"status": "scheduled"}])) == []
