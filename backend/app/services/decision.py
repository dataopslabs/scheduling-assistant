"""Orchestration: propose (mock or live) -> validate with policy -> final reply + evidence."""
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from ..config import Settings
from ..policy import evaluate
from ..schemas import DecideRequest, DecisionResponse, Evidence
from .agent import agent_facts, live_propose, mock_propose


def decide(req: DecideRequest, settings: Settings, agent: Any = None) -> DecisionResponse:
    t0, case, error, model_id = time.perf_counter(), req.case, None, None
    if req.mode == "live":
        proposed, source, error = live_propose(case, settings, agent)
        model_id = settings.model_id
    else:
        proposed, source = mock_propose(case)

    rules, findings = evaluate(case, proposed)
    ok = not findings
    return DecisionResponse(
        case_id=case.case_id, mode=req.mode, proposed_decision=proposed, acceptable=ok, findings=findings,
        final_action=proposed.action if ok else "escalate",
        final_reply=proposed.reply if ok else findings[0].safer_alternative,
        note="No real scheduling side effect is performed.",
        evidence=Evidence(
            request_id=uuid.uuid4().hex[:12], timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            latency_ms=round((time.perf_counter() - t0) * 1000), mode=req.mode, source=source, model_id=model_id,
            facts=agent_facts(case), rules=rules, error=error))
