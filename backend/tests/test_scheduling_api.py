"""Tool layer: reads come from the system of record; writes need customer agreement to a specific available slot."""
from app.schemas import SchedulingCase
from app.tools.scheduling_api import InMemorySchedulingAPI


def api(writes=False, slots=None):
    c = SchedulingCase.model_validate({"customer_message": "x", "appointment": {"status": "tentative", "date": "2026-10-13"},
                                       "crew": {"confirmation_status": "unknown"},
                                       "available_slots": slots if slots is not None else [{"date": "Monday", "start_time": "10:00"}],
                                       "other_jobs": [{"job_id": "J1", "status": "completed"}, {"job_id": "J2", "status": "scheduled"}]})
    return InMemorySchedulingAPI(c, writes_enabled=writes)


def test_reads():
    a = api()
    assert a.get_appointment().status == "tentative" and a.get_crew_confirmation() == "unknown"
    assert [s.slot_id for s in a.get_available_slots()] == ["slot-1"] and a.get_available_slots()[0].label == "Monday 10:00"
    assert {j.job_id: j.active for j in a.get_jobs()} == {"J1": False, "J2": True}


def test_booking_requires_customer_agreement():
    r = api(writes=True).book_slot("slot-1", customer_agreed=False)
    assert not r.performed and "not agreed" in r.reason


def test_booking_requires_available_slot():
    r = api(writes=True).book_slot("slot-9", customer_agreed=True)
    assert not r.performed and "not in the available" in r.reason


def test_booking_is_dry_run_by_default_and_performed_when_enabled():
    dry = api().book_slot("slot-1", True)
    assert not dry.performed and dry.dry_run
    a = api(writes=True)
    done = a.book_slot("slot-1", True)
    assert done.performed and a.booked == ["slot-1"]
