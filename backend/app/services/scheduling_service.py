"""Guarded scheduling flow (the end-to-end pipeline).

  1 RequestReviewer  message -> structured draft request              (LLM, no facts, no tools)
  2 Decider          typed judgment + confidence; < threshold -> human (LLM, no tools)
  3 Python           read verified facts, build evidence pack, own any write
  4 ResponseWriter   draft reply from the evidence pack only           (LLM, no tools)
  5 Final guard      validate every claim; one rewrite; else safe response / human

AI proposes. The Decider judges. Python verifies. The system of record confirms.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from ..agents import decider_client, request_reviewer, response_writer
from ..agents.llm import AgentSet
from ..agents.response_writer import HOLDING
from ..config import Settings
from ..policies import PRECEDENCE
from ..schemas import (DecideRequest, DecisionResponse, DraftRequest, Evidence, EvidencePack, Judgment, PipelineStep,
                       ProposedDecision, RuleResult, SchedulingCase)
from ..tools.scheduling_api import InMemorySchedulingAPI
from .evidence_builder import build_evidence_pack
from .response_guard import validate_response

NOTE = "No real scheduling side effect is performed."


def agent_facts(case: SchedulingCase) -> dict[str, Any]:
    """Facts as supplied with the case (shown in the Evidence panel): no recorded reply, no expected outcome."""
    return case.model_dump(exclude={"proposed_decision", "expected", "category", "use_case", "variant", "title", "case_id"})


def _safe_response(judgment: Judgment, findings) -> ProposedDecision:
    """Fixed safe reply. If the Decider decided to wait for the customer, the only safe reply is the acknowledgement
    (never slots or a booking push); otherwise use the alternative of the highest-precedence finding from either draft."""
    if judgment.next_action == "wait_for_customer":
        return ProposedDecision(action="wait", reply="Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment.")
    order = {rule: i for i, rule in enumerate(PRECEDENCE)}
    best = min(findings, key=lambda f: order.get(f.rule_id, 99))
    return ProposedDecision(action="escalate", reply=best.safer_alternative)


class _Trace:
    def __init__(self): self.steps: list[PipelineStep] = []
    def add(self, key, name, status, detail="", t0=None):
        self.steps.append(PipelineStep(key=key, name=name, status=status, detail=detail,
                                       ms=round((time.perf_counter() - t0) * 1000) if t0 else 0))


def run_scheduling_flow(req: DecideRequest, settings: Settings, agents: Optional[AgentSet] = None) -> DecisionResponse:
    started, case, live = time.perf_counter(), req.case, req.mode == "live"
    trace, error = _Trace(), None
    source = "bedrock" if live else ("fixture" if case.proposed_decision else "mock-agent")
    api = InMemorySchedulingAPI(case, writes_enabled=settings.writes_enabled)
    draft: Optional[DraftRequest] = None
    judgment: Optional[Judgment] = None
    pack: Optional[EvidencePack] = None
    rules: list[RuleResult] = []
    rewrite_attempted = False

    def finish(proposed, final, resolution, findings, ok_first):
        ev = Evidence(request_id=uuid.uuid4().hex[:12], timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      latency_ms=round((time.perf_counter() - started) * 1000), mode=req.mode, source=source,
                      model_id=settings.model_id if live else None, facts=agent_facts(case), rules=rules, error=error,
                      pipeline=trace.steps, draft_request=draft, judgment=judgment, evidence_pack=pack, rewrite_attempted=rewrite_attempted)
        return DecisionResponse(case_id=case.case_id, mode=req.mode, proposed_decision=proposed, acceptable=ok_first, findings=findings,
                                final_action=final.action, final_reply=final.reply, resolution=resolution, note=NOTE, evidence=ev)

    def to_human(detail: str, err: Optional[str] = None):
        nonlocal error, source
        if err:
            error, source = err, ("bedrock-fallback" if live else source)
        trace.add("human", "Human escalation", "ok", detail)
        return finish(HOLDING, HOLDING, "human_escalation", [], False)

    # 1 · request reviewer
    t = time.perf_counter()
    try:
        draft = request_reviewer.extract_request(case.customer_message, live, settings, agents)
        trace.add("request_reviewer", "Request reviewer", "ok", f"intent={draft.intent}", t)
    except Exception as exc:  # noqa: BLE001 - boundary: degrade to a human, never to raw model text
        trace.add("request_reviewer", "Request reviewer", "error", str(exc)[:160], t)
        return to_human("Reviewer failed", f"{type(exc).__name__}: {exc}"[:400])

    # 2 · decider
    t = time.perf_counter()
    try:
        judgment = decider_client.decide(draft, case.customer_message, live, settings, agents)
        trace.add("decider", "Strands Decider", "ok", f"{judgment.next_action} @ {judgment.confidence:.2f} (threshold {settings.decider_threshold})", t)
    except Exception as exc:  # noqa: BLE001
        trace.add("decider", "Strands Decider", "error", str(exc)[:160], t)
        return to_human("Decider failed", f"{type(exc).__name__}: {exc}"[:400])

    # 3 · python rules and tools
    t = time.perf_counter()
    pack = build_evidence_pack(api, case.customer_message, draft, judgment)
    detail = f"{len(pack.available_slots)} slots, {len(pack.other_jobs)} jobs" + (f", missing: {', '.join(pack.missing)}" if pack.missing else "")
    if pack.booking:
        detail += f", booking performed={pack.booking.performed} dry_run={pack.booking.dry_run}"
    trace.add("python_tools", "Python rules and tools", "ok", detail, t)

    if judgment.confidence < settings.decider_threshold or judgment.next_action == "escalate":
        trace.add("response_writer", "Response writer", "skipped", "Low confidence or escalate: routed to human")
        trace.add("final_guard", "Final response guard", "skipped")
        return to_human(f"confidence {judgment.confidence:.2f} < {settings.decider_threshold} or action=escalate")

    # 4 · response writer (mock + recorded reply: replay the simulated model output)
    t = time.perf_counter()
    try:
        if not live and case.proposed_decision is not None:
            proposed = case.proposed_decision
            trace.add("response_writer", "Response writer", "ok", "replaying recorded (simulated) model output", t)
        else:
            proposed = response_writer.write(pack, judgment, draft, live, settings, agents)
            trace.add("response_writer", "Response writer", "ok", f"action={proposed.action}", t)
    except Exception as exc:  # noqa: BLE001
        trace.add("response_writer", "Response writer", "error", str(exc)[:160], t)
        return to_human("Writer failed", f"{type(exc).__name__}: {exc}"[:400])

    # 5 · final guard
    t = time.perf_counter()
    flags: list[str] = []
    if live and settings.review_claims:
        try:
            flags = decider_client.flag_unsupported_claims(proposed.reply, pack, settings, agents)
        except Exception as exc:  # noqa: BLE001 - the extra review is advisory; the deterministic guard still runs
            error = f"claim review skipped: {type(exc).__name__}"
    first = validate_response(proposed.reply, pack, flags)
    rules = first.rules
    if first.acceptable:
        trace.add("final_guard", "Final response guard", "ok", "all claims supported by the evidence pack", t)
        return finish(proposed, proposed, "approved", [], True)
    trace.add("final_guard", "Final response guard", "blocked", "; ".join(f.rule_id.split("_")[0] for f in first.findings), t)

    # one rewrite from the evidence pack, told which claims were rejected
    t = time.perf_counter()
    rewrite_attempted = True
    try:
        rewritten = response_writer.write(pack, judgment, draft, live, settings, agents, violations=first.findings)
        second = validate_response(rewritten.reply, pack)
    except Exception as exc:  # noqa: BLE001
        rewritten, second = None, None
        error = f"{type(exc).__name__}: {exc}"[:400]
    if rewritten is not None and second is not None and second.acceptable:
        trace.add("rewrite", "One rewrite", "ok", "rewrite passed validation", t)
        return finish(proposed, rewritten, "rewritten", first.findings, False)
    trace.add("rewrite", "One rewrite", "blocked", "rewrite failed validation: using fixed safe response", t)
    safe = _safe_response(judgment, first.findings + (second.findings if second else []))
    return finish(proposed, safe, "safe_response", first.findings, False)
