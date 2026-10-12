"""E5 data uncertainty: fail closed when critical facts are missing or invalid."""
from typing import Optional
from ..schemas import PolicyFinding
from .base import VALID_APPOINTMENT, VALID_CREW, RuleContext


def check(ctx: RuleContext) -> Optional[PolicyFinding]:
    if ctx.status not in VALID_APPOINTMENT or ctx.crew not in VALID_CREW:
        return PolicyFinding(rule_id="E5_DATA_UNCERTAINTY", reason="Appointment or crew status is missing or invalid.",
                             safer_alternative="We need to verify the appointment and crew status before confirming.")
    return None
