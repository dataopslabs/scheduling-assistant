"""Final guard: validates a reply against the evidence pack (claims unsupported by evidence are rejected)."""
from app.schemas import AppointmentRecord, BookingResult, EvidencePack, JobRecord, SlotRecord
from app.services.response_guard import validate_response


def pack(**kw):
    base = dict(customer_message="hi", appointment=AppointmentRecord(date="2026-10-13", start_time="09:00", end_time="12:00", status="tentative"),
                crew_confirmation="unknown", available_slots=[SlotRecord(slot_id="slot-1", label="Monday 10:00", day="Monday", start_time="10:00")])
    base.update(kw)
    return EvidencePack(**base)


def test_unsupported_crew_promise_rejected():
    r = validate_response("Yes, the crew will be there tomorrow.", pack())
    assert not r.acceptable and r.findings[0].rule_id == "E4_CONFIRMATION_INTEGRITY"
    assert [x.status for x in r.rules if x.rule_id.startswith("E4")] == ["blocked"]


def test_supported_reply_accepted_with_all_rules_passed():
    r = validate_response("Your appointment is tentative and the crew is not yet confirmed.", pack())
    assert r.acceptable and {x.status for x in r.rules} == {"passed"}


def test_unavailable_slot_rejected_available_accepted():
    assert not validate_response("Sure, we can come Saturday.", pack()).acceptable
    assert validate_response("Monday at 10:00 is available. Would you like to proceed?", pack()).acceptable


def test_conflict_claim_needs_active_job_in_pack():
    done = pack(other_jobs=[JobRecord(job_id="j1", status="completed", active=False)])
    assert not validate_response("There is a scheduling conflict.", done).acceptable
    live = pack(other_jobs=[JobRecord(job_id="j2", status="scheduled", active=True)], active_jobs=["j2"])
    assert validate_response("There is a scheduling conflict.", live).acceptable


def test_booking_claim_requires_performed_booking_in_pack():
    assert not validate_response("Great, you're booked for Monday.", pack(booking=BookingResult(slot_id="slot-1", performed=False, dry_run=True, reason="dry"))).acceptable
    assert validate_response("Great, you're booked for Monday.", pack(booking=BookingResult(slot_id="slot-1", performed=True, dry_run=False, reason="ok"))).acceptable


def test_decider_flags_can_only_add_findings():
    r = validate_response("Your appointment is tentative.", pack(), extra_flags=["mentions a discount"])
    assert not r.acceptable and r.findings[-1].rule_id == "DECIDER_FLAG"


def test_missing_facts_fail_closed():
    r = validate_response("Everything is confirmed.", pack(appointment=None, crew_confirmation=None))
    assert not r.acceptable and r.findings[0].rule_id == "E5_DATA_UNCERTAINTY"
    assert [x.status for x in r.rules if not x.rule_id.startswith("E5")] == ["skipped"] * 4
