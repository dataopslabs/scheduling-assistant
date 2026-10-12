"""Shared types, vocabularies and helpers for the deterministic policy rules.

Rules never call a model. They check the claims in a reply against verified facts,
which come either from a raw test case or from the evidence pack built by Python.
"""
import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..schemas import EvidencePack, SchedulingCase

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
VALID_APPOINTMENT = {"confirmed", "tentative", "pending", "cancelled", "completed", "none"}
VALID_CREW = {"confirmed", "unknown", "pending", "unconfirmed", "cancelled"}
ACTIVE_JOB = {"scheduled", "in_progress", "active", "confirmed"}

AFFIRM = re.compile(r"\b(yes|sure|absolutely|we can|we will|we'll|confirmed for|booked for|see you|you're (all )?set)\b")
NEGATE = re.compile(r"\b(not|cannot|can't|unable|unfortunately|unavailable|sorry|no availability)\b|n't\b")
UNCERTAIN = re.compile(r"\b(not|tentative|unknown|unconfirmed|pending|yet|once|until|if|need to confirm|check and update)\b|n't\b")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\s+[—–]\s+", text) if s.strip()]


@dataclass(frozen=True)
class RuleContext:
    reply: str                      # casefolded reply under test
    message: str                    # casefolded customer message
    status: str                     # appointment status
    crew: str                       # crew confirmation status
    appt_date: Optional[str]
    slots: tuple[dict, ...]         # authoritative availability
    jobs: tuple[dict, ...]          # other jobs on record
    booking_performed: bool = False

    @classmethod
    def from_case(cls, case: "SchedulingCase", reply: str) -> "RuleContext":
        return cls(reply.casefold(), case.customer_message.casefold(), (case.appointment.status or "").casefold(),
                   (case.crew.confirmation_status or "").casefold(), case.appointment.date,
                   tuple(case.available_slots), tuple(case.other_jobs))

    @classmethod
    def from_pack(cls, pack: "EvidencePack", reply: str) -> "RuleContext":
        a = pack.appointment
        return cls(reply.casefold(), pack.customer_message.casefold(), ((a.status if a else "") or "").casefold(),
                   (pack.crew_confirmation or "").casefold(), a.date if a else None,
                   tuple({"date": s.date, "day": s.day, "start_time": s.start_time} for s in pack.available_slots),
                   tuple({"job_id": j.job_id, "status": j.status} for j in pack.other_jobs),
                   bool(pack.booking and pack.booking.performed))


def slot_days(slots) -> set[str]:
    """Weekday names covered by availability; slots may carry a weekday name or an ISO date."""
    days: set[str] = set()
    for s in slots:
        raw = str(s.get("day") or s.get("date") or "").casefold().strip()
        if raw in WEEKDAYS:
            days.add(raw)
        else:
            try:
                days.add(WEEKDAYS[date.fromisoformat(raw[:10]).weekday()])
            except ValueError:
                pass
    return days


def weekday_of(iso: Optional[str]) -> Optional[str]:
    try:
        return WEEKDAYS[date.fromisoformat(iso or "").weekday()]
    except ValueError:
        return None
