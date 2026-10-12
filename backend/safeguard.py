"""Deterministic safeguards for the AI scheduling assistant (cases A-D).

The model proposes a decision. Before it reaches the customer, `check_decision` verifies the
claims the decision makes against the supplied facts. On failure it returns a reason and a safer
alternative built only from those facts.

Rules (first failure wins):
  C  slot      - never commit to a time that is not an available slot / the existing appointment
  D  status    - never state more certainty than the status fields support
  A  conflict  - only claim a conflict when an ACTIVE job of the same crew overlaps in time
  B  deferral  - if the customer says they will get back to us, wait; do not push a booking
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, Optional

Action = Literal["reply", "wait", "escalate"]
ACTIVE_STATUSES = ("scheduled", "in_progress")


# --------------------------------------------------------------------------- data model
@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime

    def label(self) -> str:
        return f"{self.start:%A %d %b} at {self.start:%H:%M}"


@dataclass(frozen=True)
class Job:
    start: datetime
    end: datetime
    crew: str
    status: Literal["scheduled", "in_progress", "completed", "cancelled"]


@dataclass(frozen=True)
class Appointment:
    start: datetime
    end: datetime
    status: Literal["confirmed", "tentative"]
    crew: Optional[str] = None
    crew_confirmed: Optional[bool] = None  # None = unknown


@dataclass(frozen=True)
class SchedulingFacts:
    now: datetime  # reference for "today", "tomorrow", "this Saturday"
    customer_message: str = ""
    available_slots: tuple[Slot, ...] = ()
    appointment: Optional[Appointment] = None
    other_jobs: tuple[Job, ...] = ()


@dataclass(frozen=True)
class ProposedDecision:
    action: Action
    message: str
    committed_slot_start: Optional[datetime] = None  # slot the model claims to confirm/book


@dataclass(frozen=True)
class CheckResult:
    acceptable: bool
    reason: str
    safer_alternative: Optional[ProposedDecision] = None
    rule: Optional[str] = None  # slot | status | conflict | deferral


# --------------------------------------------------------------------------- text helpers
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_DAY_RE = re.compile(r"\b(today|tomorrow|" + "|".join(WEEKDAYS) + r")\b", re.I)
_AFFIRM_RE = re.compile(
    r"\b(yes|sure|absolutely|we can|we will|we'll|confirmed|booked|see you|will be there)\b", re.I
)
_NEGATE_RE = re.compile(
    r"\b(not|cannot|unable|unfortunately|unavailable|sorry)\b|n't\b|\bno availability\b", re.I
)
_UNCERTAIN_RE = re.compile(
    r"\b(not|tentative|unknown|unconfirmed|yet|pending|once|until|if|unfortunately)\b|n't\b", re.I
)
_CREW_CLAIM_RE = re.compile(
    r"\b(crew|team|technicians?|installers?)\b.*\b(will be there|is coming|are coming|will arrive|"
    r"will come|is on (the|their) way)\b|\b(will be there|see you)\b", re.I
)
_CONFIRMED_CLAIM_RE = re.compile(r"\bconfirmed\b|\bis (all )?set\b|\bis booked\b", re.I)
_CONFLICT_CLAIM_RE = re.compile(r"\b(conflicts?|double[- ]?book\w*|clash\w*|delayed?)\b", re.I)
_DEFER_RE = re.compile(
    r"(i'?ll|i will) (let you know|get back|contact|reach out|call|message)|when i'?m back|"
    r"i'?m (away|travell?ing)|out of town|on (holiday|vacation)", re.I
)
_PUSH_RE = re.compile(r"\?|\b(book|schedule|how about|would you like|shall we|can we)\b", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\s+[—–]\s+")


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _resolve_day(word: str, now: datetime) -> date:
    word = word.lower()
    today = now.date()
    if word == "today":
        return today
    if word == "tomorrow":
        return today + timedelta(days=1)
    ahead = (WEEKDAYS.index(word) - today.weekday()) % 7  # next occurrence, today included
    return today + timedelta(days=ahead)


def _affirmed_dates(message: str, now: datetime) -> list[date]:
    """Dates the message says yes to. Sentences containing a negation are skipped."""
    dates: list[date] = []
    for sentence in _sentences(message):
        if _AFFIRM_RE.search(sentence) and not _NEGATE_RE.search(sentence):
            dates += [_resolve_day(m.group(1), now) for m in _DAY_RE.finditer(sentence)]
    return dates


def _day_label(d: date, now: datetime) -> str:
    if d == now.date() + timedelta(days=1):
        return "tomorrow"
    if d == now.date():
        return "today"
    return f"{d:%A %d %b}"


# --------------------------------------------------------------------------- alternatives
def safer_alternative(facts: SchedulingFacts, unavailable: str) -> ProposedDecision:
    slots = sorted(facts.available_slots, key=lambda s: s.start)[:3]
    if not slots:
        return ProposedDecision(
            action="escalate",
            message=(f"I'm sorry, we don't have availability on {unavailable}. "
                     "I've asked our scheduling team to find you a time and they'll be in touch."),
        )
    options = " or ".join(s.label() for s in slots)
    return ProposedDecision(
        action="reply",
        message=(f"I'm sorry, we don't have availability on {unavailable}. "
                 f"The next open slots are {options}. Would either of those work for you?"),
    )


def status_reply(facts: SchedulingFacts) -> ProposedDecision:
    """Honest answer about the existing appointment, strictly from its status fields."""
    a = facts.appointment
    if a is None:
        return ProposedDecision(
            "escalate",
            "I can't find an appointment for you, so I've asked our team to check and get back to you.",
        )
    when = f"{_day_label(a.start.date(), facts.now)}, {a.start:%H:%M}–{a.end:%H:%M}"
    if a.status == "confirmed" and a.crew_confirmed is not False:
        return ProposedDecision("reply", f"Yes — your installation is confirmed for {when}.")
    return ProposedDecision(
        "escalate",
        f"Your appointment {when} is still tentative and the crew hasn't been confirmed yet. "
        "I've asked our team to confirm and we'll update you as soon as we know.",
    )


# --------------------------------------------------------------------------- rules
def _fail(rule: str, reason: str, alt: ProposedDecision) -> CheckResult:
    return CheckResult(False, reason, alt, rule)


def _rule_slot(facts: SchedulingFacts, d: ProposedDecision) -> Optional[CheckResult]:
    starts = {s.start for s in facts.available_slots}
    dates = {s.start.date() for s in facts.available_slots}
    if facts.appointment:  # restating the existing appointment is not a new commitment
        starts.add(facts.appointment.start)
        dates.add(facts.appointment.start.date())

    if d.committed_slot_start is not None and d.committed_slot_start not in starts:
        when = f"{d.committed_slot_start:%A %d %b %H:%M}"
        return _fail("slot", f"Decision commits to {when}, which is not an available slot.",
                     safer_alternative(facts, f"{d.committed_slot_start:%A %d %b}"))

    for day in _affirmed_dates(d.message, facts.now):
        if day not in dates:
            avail = ", ".join(s.label() for s in facts.available_slots) or "none"
            return _fail("slot",
                         f"Message confirms {day:%A %d %b}, but there is no available slot that day "
                         f"(available: {avail}).",
                         safer_alternative(facts, f"{day:%A %d %b}"))
    return None


def _rule_status(facts: SchedulingFacts, d: ProposedDecision) -> Optional[CheckResult]:
    a = facts.appointment
    if a is None:
        return None
    for s in _sentences(d.message):
        if _UNCERTAIN_RE.search(s):
            continue
        if _CREW_CLAIM_RE.search(s) and a.crew_confirmed is not True:
            state = "unknown" if a.crew_confirmed is None else "not confirmed"
            return _fail("status", f"Message promises the crew will attend, but crew confirmation is "
                                   f"{state} (appointment is {a.status}).", status_reply(facts))
        if _CONFIRMED_CLAIM_RE.search(s) and a.status != "confirmed":
            return _fail("status", f"Message says the appointment is confirmed, but its status is "
                                   f"'{a.status}'.", status_reply(facts))
    return None


def _rule_conflict(facts: SchedulingFacts, d: ProposedDecision) -> Optional[CheckResult]:
    a = facts.appointment
    if a is None or not _CONFLICT_CLAIM_RE.search(d.message):
        return None
    if any(_CONFLICT_CLAIM_RE.search(s) and _NEGATE_RE.search(s) for s in _sentences(d.message)):
        return None
    overlapping = [j for j in facts.other_jobs
                   if j.crew == a.crew and j.status in ACTIVE_STATUSES
                   and j.start < a.end and a.start < j.end]
    if overlapping:
        return None
    inactive = [j for j in facts.other_jobs if j.crew == a.crew and j.status not in ACTIVE_STATUSES]
    why = (f"{len(inactive)} other job(s) for the same crew are {'/'.join(sorted({j.status for j in inactive}))}, "
           "which cannot conflict" if inactive else "no other active job overlaps this appointment")
    return _fail("conflict", f"Message claims a scheduling conflict, but {why}.", status_reply(facts))


def _rule_deferral(facts: SchedulingFacts, d: ProposedDecision) -> Optional[CheckResult]:
    if not _DEFER_RE.search(facts.customer_message):
        return None
    if d.action == "wait" and not _PUSH_RE.search(d.message):
        return None
    return _fail("deferral",
                 "Customer said they will get back to us, but the decision "
                 f"{'pushes a booking' if _PUSH_RE.search(d.message) else 'is not a wait'}.",
                 ProposedDecision("wait", "No problem — just message us when you're back and "
                                          "we'll find a time that suits you."))


_RULES = (_rule_slot, _rule_status, _rule_conflict, _rule_deferral)


def check_decision(facts: SchedulingFacts, decision: ProposedDecision) -> CheckResult:
    for rule in _RULES:
        failure = rule(facts, decision)
        if failure:
            return failure
    return CheckResult(True, "All claims are supported by the supplied facts.")


def apply_guard(facts: SchedulingFacts, decision: ProposedDecision) -> tuple[ProposedDecision, CheckResult]:
    """Return the decision that may be sent to the customer, plus the verdict."""
    result = check_decision(facts, decision)
    return (decision if result.acceptable else result.safer_alternative), result
