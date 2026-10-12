"""Step 5: final response guard. Validates every date, slot, status, confirmation and conflict claim of a reply
against the evidence pack using the deterministic policies. A failed validation is never silently bypassed."""
from dataclasses import dataclass
from ..policies import evaluate
from ..policies.base import RuleContext
from ..schemas import EvidencePack, PolicyFinding, RuleResult


@dataclass(frozen=True)
class GuardResult:
    acceptable: bool
    rules: list[RuleResult]
    findings: list[PolicyFinding]


def validate_response(reply: str, pack: EvidencePack, extra_flags: list[str] | None = None) -> GuardResult:
    rules, findings = evaluate(RuleContext.from_pack(pack, reply))
    findings = list(findings)
    for flag in extra_flags or []:   # decider-flagged unsupported claims can only add findings
        findings.append(PolicyFinding(rule_id="DECIDER_FLAG", reason=f"Decider flagged an unsupported claim: {flag}",
                                      safer_alternative="Thanks - I've passed your request to our scheduling team and they'll reply shortly."))
    return GuardResult(not findings, rules, findings)
