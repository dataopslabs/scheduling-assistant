"""E1 conflict accuracy: completed or cancelled jobs are not conflicts."""
import re
from typing import Optional
from ..schemas import PolicyFinding
from .base import ACTIVE_JOB, RuleContext, sentences

# Negation for conflict claims is narrower: "Unfortunately there is a conflict" is still a claim.
NEGATE_CLAIM = re.compile(r"\b(no|not|never|without|isn't|aren't|doesn't|don't)\b|n't\b")
CONFLICT_CLAIM = re.compile(r"\b(conflicts?|double[- ]?book\w*|clash\w*|delayed?)\b")


def active_jobs(jobs) -> list[dict]:
    return [j for j in jobs if str(j.get("status", "")).casefold() in ACTIVE_JOB]


def check(ctx: RuleContext) -> Optional[PolicyFinding]:
    claims = [s for s in sentences(ctx.reply) if CONFLICT_CLAIM.search(s) and not NEGATE_CLAIM.search(s)]
    if claims and not active_jobs(ctx.jobs):
        return PolicyFinding(rule_id="E1_CONFLICT_ACCURACY",
                             reason="No active job supports the claimed conflict (completed/cancelled jobs cannot conflict).",
                             safer_alternative="Your appointment is currently listed as confirmed. We will verify any active conflict before escalating.")
    return None
