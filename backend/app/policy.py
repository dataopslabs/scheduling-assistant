"""Backward-compatible entry points used by the evaluation CLI and tests.
The rules themselves live in app/policies/ (one module per concern)."""
from .policies import RULES, evaluate as _evaluate
from .policies.base import RuleContext
from .schemas import PolicyFinding, ProposedDecision, RuleResult, SchedulingCase

__all__ = ["RULES", "evaluate", "validate"]


def evaluate(case: SchedulingCase, decision: ProposedDecision) -> tuple[list[RuleResult], list[PolicyFinding]]:
    return _evaluate(RuleContext.from_case(case, decision.reply))


def validate(case: SchedulingCase, decision: ProposedDecision) -> list[PolicyFinding]:
    return evaluate(case, decision)[1]
