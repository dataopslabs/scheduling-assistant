"""E3 availability integrity: only slots in the authoritative list may be offered or affirmed."""
import re
from typing import Optional
from ..schemas import PolicyFinding
from .base import AFFIRM, NEGATE, WEEKDAYS, RuleContext, sentences, slot_days, weekday_of


def is_slot_available(requested_day: Optional[str], requested_time: Optional[str], slots) -> bool:
    """True only if a slot matches the requested weekday (and time, when given). Pure; used by tools and tests."""
    if not requested_day:
        return False
    day = requested_day.casefold()
    for s in slots:
        if day in slot_days([s]):
            t = s.get("start_time") or s.get("time")
            if not requested_time or not t or str(t) == requested_time:
                return True
    return False


def unavailable_alt(day: str, slots) -> str:
    labels = [f"{x.get('date') or x.get('day')} {x.get('start_time') or x.get('time') or ''}".strip() for x in slots]
    if not labels:
        return f"Sorry, we don't have {day.capitalize()} availability. I've asked our scheduling team to find you a time."
    return f"Sorry, we don't have {day.capitalize()} availability. We can offer: {' or '.join(labels[:3])}. Would one of those work?"


def check(ctx: RuleContext) -> Optional[PolicyFinding]:
    """Never affirm a weekday that has no slot (nor the existing appointment day)."""
    days, appt_day = slot_days(ctx.slots), weekday_of(ctx.appt_date)
    for s in sentences(ctx.reply):
        if AFFIRM.search(s) and not NEGATE.search(s):
            for d in WEEKDAYS:
                if re.search(rf"\b{d}\b", s) and d not in days and d != appt_day:
                    return PolicyFinding(rule_id="E3_AVAILABILITY_INTEGRITY",
                                         reason=f"Reply affirms {d.capitalize()} but no {d.capitalize()} slot exists in supplied availability.",
                                         safer_alternative=unavailable_alt(d, ctx.slots))
    return None
