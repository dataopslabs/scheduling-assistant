"""E2 customer intent: if the customer says they will get back to us, do not push a booking."""
import re
from typing import Optional
from ..schemas import PolicyFinding
from .base import RuleContext

DEFER = re.compile(r"(i'?ll|i will) (let you know|get back|contact|reach out|call|message)|when i'?m back|when i am back|i'?m away|out of town")
PUSH = re.compile(r"\?|\bbook you\b|\bshall we\b|\bhow about\b|\bwould you like\b|\bcan we book\b")


def check(ctx: RuleContext) -> Optional[PolicyFinding]:
    if DEFER.search(ctx.message) and PUSH.search(ctx.reply):
        return PolicyFinding(rule_id="E2_CUSTOMER_INTENT",
                             reason="Reply proposes booking despite the customer saying they will update later.",
                             safer_alternative="Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment.")
    return None
