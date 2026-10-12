"""E4 confirmation integrity: unknown or tentative status can never become a promise."""
import re
from typing import Optional
from ..schemas import PolicyFinding
from .base import UNCERTAIN, RuleContext, sentences

CREW_PROMISE = re.compile(
    r"\b(crew|team|technicians?|installers?)\b.*\b(will be there|is coming|are coming|will arrive|will come|is on (the|their) way|is confirmed)\b"
    r"|\bwe(?:'ll| will) be there\b|\byou can count on us\b|\bsee you\b")
BOOKING_CLAIM = re.compile(r"\byou(?:'re| are) (?:all )?(?:booked|set)\b|\bbooked for\b|\bwe(?:'ve| have) booked\b|\byour booking is confirmed\b")
ALT = "Your appointment is not yet fully confirmed. We will check crew availability and update you."


def check(ctx: RuleContext) -> Optional[PolicyFinding]:
    for s in sentences(ctx.reply):
        if UNCERTAIN.search(s):
            continue
        if CREW_PROMISE.search(s) and ctx.crew != "confirmed":
            return PolicyFinding(rule_id="E4_CONFIRMATION_INTEGRITY",
                                 reason="Reply promises attendance while crew confirmation is not confirmed.", safer_alternative=ALT)
        if re.search(r"\bconfirmed\b", s) and ctx.status not in ("confirmed", "completed"):
            return PolicyFinding(rule_id="E4_CONFIRMATION_INTEGRITY",
                                 reason=f"Reply says confirmed while appointment status is '{ctx.status}'.", safer_alternative=ALT)
        if BOOKING_CLAIM.search(s) and not ctx.booking_performed and ctx.status != "confirmed":
            return PolicyFinding(rule_id="E4_CONFIRMATION_INTEGRITY",
                                 reason="Reply says a booking was made, but no booking was performed by the scheduling system.",
                                 safer_alternative="Thanks - I've passed your request to our scheduling team. You'll receive a confirmation once it is finalised.")
    return None
