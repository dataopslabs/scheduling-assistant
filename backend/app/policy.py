"""Deterministic policy validator: the model proposes, this code disposes.

Rules E1-E4 map to the four source cases; E5 fails closed on missing/invalid facts.
Phrase checks are heuristics (see README limitations); they are written to generalise beyond the
exact fixture sentences (any weekday, any attendance promise, any conflict wording).
"""
import re
from datetime import date
from dataclasses import dataclass
from typing import Callable, Optional
from .schemas import SchedulingCase, ProposedDecision, PolicyFinding, RuleResult

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
VALID_APPOINTMENT = {"confirmed", "tentative", "pending", "cancelled", "completed", "none"}
VALID_CREW = {"confirmed", "unknown", "pending", "unconfirmed", "cancelled"}
ACTIVE_JOB = {"scheduled", "in_progress", "active", "confirmed"}

AFFIRM = re.compile(r"\b(yes|sure|absolutely|we can|we will|we'll|confirmed for|booked for|see you|you're (all )?set)\b")
NEGATE = re.compile(r"\b(not|cannot|can't|unable|unfortunately|unavailable|sorry|no availability)\b|n't\b")
UNCERTAIN = re.compile(r"\b(not|tentative|unknown|unconfirmed|pending|yet|once|until|if|need to confirm|check and update)\b|n't\b")
CREW_PROMISE = re.compile(
    r"\b(crew|team|technicians?|installers?)\b.*\b(will be there|is coming|are coming|will arrive|will come|is on (the|their) way|is confirmed)\b"
    r"|\bwe(?:'ll| will) be there\b|\byou can count on us\b|\bsee you\b")
CONFLICT_CLAIM = re.compile(r"\b(conflicts?|double[- ]?book\w*|clash\w*|delayed?)\b")
DEFER = re.compile(r"(i'?ll|i will) (let you know|get back|contact|reach out|call|message)|when i'?m back|when i am back|i'?m away|out of town")
PUSH = re.compile(r"\?|\bbook you\b|\bshall we\b|\bhow about\b|\bwould you like\b|\bcan we book\b")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\s+[—–]\s+", text) if s.strip()]


def _slot_days(case: SchedulingCase) -> set[str]:
    """Weekday names covered by availability; slots may carry a weekday name or an ISO date."""
    days: set[str] = set()
    for s in case.available_slots:
        raw = str(s.get("day") or s.get("date") or "").casefold().strip()
        if raw in WEEKDAYS:
            days.add(raw)
        else:
            try:
                days.add(WEEKDAYS[date.fromisoformat(raw[:10]).weekday()])
            except ValueError:
                pass
    return days


@dataclass(frozen=True)
class Ctx:
    case: SchedulingCase
    reply: str      # casefolded proposed reply
    msg: str        # casefolded customer message
    status: str     # appointment status
    crew: str       # crew confirmation status


def _f(rule: str, reason: str, alt: str) -> PolicyFinding:
    return PolicyFinding(rule_id=rule, reason=reason, safer_alternative=alt)


def e1_conflict(c: Ctx) -> Optional[PolicyFinding]:
    """A conflict claim needs an ACTIVE other job."""
    claims = [s for s in _sentences(c.reply) if CONFLICT_CLAIM.search(s) and not NEGATE.search(s)]
    if claims and not any(str(j.get("status", "")).casefold() in ACTIVE_JOB for j in c.case.other_jobs):
        return _f("E1_CONFLICT_ACCURACY", "No active job supports the claimed conflict (completed/cancelled jobs cannot conflict).",
                  "Your appointment is currently listed as confirmed. We will verify any active conflict before escalating.")


def e2_intent(c: Ctx) -> Optional[PolicyFinding]:
    """Customer said they will update later: do not push a booking."""
    if DEFER.search(c.msg) and PUSH.search(c.reply):
        return _f("E2_CUSTOMER_INTENT", "Reply proposes booking despite the customer saying they will update later.",
                  "Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment.")


def _unavailable_alt(day: str, case: SchedulingCase) -> str:
    slots = [f"{x.get('date') or x.get('day')} {x.get('start_time') or x.get('time') or ''}".strip() for x in case.available_slots]
    if not slots:
        return f"Sorry, we don't have {day.capitalize()} availability. I've asked our scheduling team to find you a time."
    return f"Sorry, we don't have {day.capitalize()} availability. We can offer: {' or '.join(slots[:3])}. Would one of those work?"


def e3_availability(c: Ctx) -> Optional[PolicyFinding]:
    """Never affirm a weekday that has no slot in authoritative availability."""
    days = _slot_days(c.case)
    try:
        appt_day = WEEKDAYS[date.fromisoformat(c.case.appointment.date or "").weekday()]
    except ValueError:
        appt_day = None
    for s in _sentences(c.reply):
        if AFFIRM.search(s) and not NEGATE.search(s):
            for d in WEEKDAYS:
                if re.search(rf"\b{d}\b", s) and d not in days and d != appt_day:
                    return _f("E3_AVAILABILITY_INTEGRITY",
                              f"Reply affirms {d.capitalize()} but no {d.capitalize()} slot exists in supplied availability.",
                              _unavailable_alt(d, c.case))


def e4_confirmation(c: Ctx) -> Optional[PolicyFinding]:
    """Attendance promise needs confirmed crew; 'confirmed' needs a confirmed appointment."""
    alt = "Your appointment is not yet fully confirmed. We will check crew availability and update you."
    for s in _sentences(c.reply):
        if UNCERTAIN.search(s):
            continue
        if CREW_PROMISE.search(s) and c.crew != "confirmed":
            return _f("E4_CONFIRMATION_INTEGRITY", "Reply promises attendance while crew confirmation is not confirmed.", alt)
        if re.search(r"\bconfirmed\b", s) and c.status not in ("confirmed", "completed"):
            return _f("E4_CONFIRMATION_INTEGRITY", f"Reply says confirmed while appointment status is '{c.status}'.", alt)


def e5_data(c: Ctx) -> Optional[PolicyFinding]:
    """Fail closed on missing/invalid critical facts."""
    if c.status not in VALID_APPOINTMENT or c.crew not in VALID_CREW:
        return _f("E5_DATA_UNCERTAINTY", "Appointment or crew status is missing or invalid.",
                  "We need to verify the appointment and crew status before confirming.")


RuleFn = Callable[[Ctx], Optional[PolicyFinding]]
# Display order (E1..E5) and human names
RULES: list[tuple[str, str, RuleFn]] = [
    ("E1_CONFLICT_ACCURACY", "Conflict accuracy", e1_conflict),
    ("E2_CUSTOMER_INTENT", "Customer intent", e2_intent),
    ("E3_AVAILABILITY_INTEGRITY", "Availability integrity", e3_availability),
    ("E4_CONFIRMATION_INTEGRITY", "Confirmation integrity", e4_confirmation),
    ("E5_DATA_UNCERTAINTY", "Data completeness", e5_data),
]
# Precedence when several rules fire: data first, then confirmation, availability, intent, conflict.
_PRECEDENCE = ["E5_DATA_UNCERTAINTY", "E4_CONFIRMATION_INTEGRITY", "E3_AVAILABILITY_INTEGRITY",
               "E2_CUSTOMER_INTENT", "E1_CONFLICT_ACCURACY"]


def _ctx(case: SchedulingCase, decision: ProposedDecision) -> Ctx:
    return Ctx(case, decision.reply.casefold(), case.customer_message.casefold(),
               (case.appointment.status or "").casefold(), (case.crew.confirmation_status or "").casefold())


def evaluate(case: SchedulingCase, decision: ProposedDecision) -> tuple[list[RuleResult], list[PolicyFinding]]:
    """Run every rule. Returns (per-rule results in display order, findings in precedence order).
    If E5 fails, the other rules are skipped (fail closed: the facts cannot be trusted)."""
    ctx = _ctx(case, decision)
    e5 = e5_data(ctx)
    results, found = [], {}
    for rule_id, name, fn in RULES:
        if e5 and rule_id != "E5_DATA_UNCERTAINTY":
            results.append(RuleResult(rule_id=rule_id, name=name, status="skipped", reason="Skipped: facts incomplete (E5)"))
            continue
        f = fn(ctx)
        if f:
            found[rule_id] = f
        results.append(RuleResult(rule_id=rule_id, name=name, status="blocked" if f else "passed", reason=f.reason if f else None))
    return results, [found[r] for r in _PRECEDENCE if r in found]


def validate(case: SchedulingCase, decision: ProposedDecision) -> list[PolicyFinding]:
    return evaluate(case, decision)[1]
