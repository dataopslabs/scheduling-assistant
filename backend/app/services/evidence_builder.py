"""Step 3 (Python): read verified facts from the scheduling API and build the evidence pack.
This is the only place where facts enter the pipeline; agents and the guard rely on the pack, nothing else."""
from ..agents.request_reviewer import message_confirms_slot
from ..policies.availability_rules import is_slot_available
from ..policies.base import VALID_APPOINTMENT, VALID_CREW, slot_days
from ..schemas import DraftRequest, EvidencePack, Judgment, RequestedSlot
from ..tools.scheduling_api import SchedulingAPI


def build_evidence_pack(api: SchedulingAPI, message: str, draft: DraftRequest, judgment: Judgment) -> EvidencePack:
    appt, crew = api.get_appointment(), api.get_crew_confirmation()
    slots, jobs = api.get_available_slots(), api.get_jobs()

    missing = []
    if not appt or (appt.status or "").casefold() not in VALID_APPOINTMENT:
        missing.append("appointment.status")
    if (crew or "").casefold() not in VALID_CREW:
        missing.append("crew.confirmation_status")

    raw = [{"day": s.day, "date": s.date, "start_time": s.start_time} for s in slots]
    requested = RequestedSlot(day=draft.requested_day, time=draft.requested_time)
    if draft.requested_day:
        for s in slots:
            if is_slot_available(draft.requested_day, draft.requested_time, [{"day": s.day, "date": s.date, "start_time": s.start_time}]):
                requested.matched_slot_id = s.slot_id
                break

    pack = EvidencePack(customer_message=message, appointment=appt, crew_confirmation=crew, available_slots=slots, other_jobs=jobs,
                        active_jobs=[j.job_id for j in jobs if j.active], requested=requested,
                        data_complete=not missing, missing=missing)

    # Writes happen here, in Python, and only for a customer-agreed, still-available slot. The agreement is verified
    # deterministically on the raw message; an LLM saying "confirms_slot" is not enough.
    if judgment.next_action == "book_slot" and draft.confirms_slot and message_confirms_slot(message) and requested.matched_slot_id:
        pack.booking = api.book_slot(requested.matched_slot_id, customer_agreed=True)
    return pack
