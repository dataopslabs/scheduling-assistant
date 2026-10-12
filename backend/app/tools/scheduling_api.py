"""Scheduling API tool layer: the ONLY component that reads the system of record and performs writes.

LLM agents never receive this object. Python orchestration calls it, builds an evidence pack from the
reads, and performs a write only after explicit customer agreement to a specific available slot.
The demo implementation is backed by the synthetic case and its writes are dry-run unless enabled.
"""
from typing import Optional, Protocol
from ..policies.availability_rules import is_slot_available
from ..schemas import AppointmentRecord, BookingResult, JobRecord, SchedulingCase, SlotRecord
from ..policies.base import ACTIVE_JOB, slot_days


class SchedulingAPI(Protocol):
    def get_appointment(self) -> Optional[AppointmentRecord]: ...
    def get_crew_confirmation(self) -> Optional[str]: ...
    def get_available_slots(self) -> list[SlotRecord]: ...
    def get_jobs(self) -> list[JobRecord]: ...
    def book_slot(self, slot_id: str, customer_agreed: bool) -> BookingResult: ...


class InMemorySchedulingAPI:
    def __init__(self, case: SchedulingCase, writes_enabled: bool = False):
        self._case, self._writes = case, writes_enabled
        self.booked: list[str] = []

    # ---- reads -----------------------------------------------------------------
    def get_appointment(self) -> Optional[AppointmentRecord]:
        a = self._case.appointment
        return AppointmentRecord(**a.model_dump()) if any(v is not None for v in a.model_dump().values()) else None

    def get_crew_confirmation(self) -> Optional[str]:
        return self._case.crew.confirmation_status

    def get_available_slots(self) -> list[SlotRecord]:
        out = []
        for i, s in enumerate(self._case.available_slots, 1):
            day = s.get("day") or s.get("date")
            t = s.get("start_time") or s.get("time")
            out.append(SlotRecord(slot_id=f"slot-{i}", label=f"{day} {t or ''}".strip(), date=s.get("date"), day=s.get("day"), start_time=t))
        return out

    def get_jobs(self) -> list[JobRecord]:
        return [JobRecord(job_id=str(j.get("job_id") or f"job-{i}"), status=str(j.get("status", "")).casefold(),
                          active=str(j.get("status", "")).casefold() in ACTIVE_JOB)
                for i, j in enumerate(self._case.other_jobs, 1)]

    # ---- writes (guarded) --------------------------------------------------------
    def book_slot(self, slot_id: str, customer_agreed: bool) -> BookingResult:
        """Book only when the customer agreed to this specific slot and it is still available."""
        if not customer_agreed:
            return BookingResult(slot_id=slot_id, performed=False, dry_run=False, reason="Customer has not agreed to a specific slot.")
        slot = next((s for s in self.get_available_slots() if s.slot_id == slot_id), None)
        if slot is None or not is_slot_available(next(iter(slot_days([{"day": slot.day, "date": slot.date}])), None), slot.start_time, self._case.available_slots):
            return BookingResult(slot_id=slot_id, performed=False, dry_run=False, reason="Slot is not in the available-slot list.")
        if not self._writes:
            return BookingResult(slot_id=slot_id, performed=False, dry_run=True, reason="Dry run: scheduling writes are disabled in this environment.")
        self.booked.append(slot_id)
        return BookingResult(slot_id=slot_id, performed=True, dry_run=False, reason="Booked.")
