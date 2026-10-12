"""Deterministic policy rules E1-E5. `evaluate` runs them all and reports per-rule results."""
from typing import Callable, Optional
from ..schemas import PolicyFinding, RuleResult
from . import availability_rules, conflict_rules, confirmation_rules, data_rules, intent_rules
from .base import RuleContext

RuleFn = Callable[[RuleContext], Optional[PolicyFinding]]
# (rule id, display name, function) in display order E1..E5
RULES: list[tuple[str, str, RuleFn]] = [
    ("E1_CONFLICT_ACCURACY", "Conflict accuracy", conflict_rules.check),
    ("E2_CUSTOMER_INTENT", "Customer intent", intent_rules.check),
    ("E3_AVAILABILITY_INTEGRITY", "Availability integrity", availability_rules.check),
    ("E4_CONFIRMATION_INTEGRITY", "Confirmation integrity", confirmation_rules.check),
    ("E5_DATA_UNCERTAINTY", "Data completeness", data_rules.check),
]
# When several rules fire, the first listed provides the safe alternative. E2 outranks E3/E4: if the customer said
# they will get back to us, the right safe reply is "wait", not an offer of slots or a status lecture.
PRECEDENCE = ["E5_DATA_UNCERTAINTY", "E2_CUSTOMER_INTENT", "E4_CONFIRMATION_INTEGRITY", "E3_AVAILABILITY_INTEGRITY",
              "E1_CONFLICT_ACCURACY"]


def evaluate(ctx: RuleContext) -> tuple[list[RuleResult], list[PolicyFinding]]:
    """Run every rule. If E5 fails the other rules are skipped (fail closed: facts cannot be trusted)."""
    e5 = data_rules.check(ctx)
    results: list[RuleResult] = []
    found: dict[str, PolicyFinding] = {}
    for rule_id, name, fn in RULES:
        if e5 and rule_id != "E5_DATA_UNCERTAINTY":
            results.append(RuleResult(rule_id=rule_id, name=name, status="skipped", reason="Skipped: facts incomplete (E5)"))
            continue
        f = fn(ctx)
        if f:
            found[rule_id] = f
        results.append(RuleResult(rule_id=rule_id, name=name, status="blocked" if f else "passed", reason=f.reason if f else None))
    return results, [found[r] for r in PRECEDENCE if r in found]
