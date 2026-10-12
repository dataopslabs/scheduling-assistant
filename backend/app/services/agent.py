"""Proposers: a Strands Agent on Amazon Bedrock (live) and a deterministic mock agent.

An agent only PROPOSES {action, reply}. It never decides what reaches the customer.
"""
import json
from typing import Any
from ..config import Settings
from ..schemas import SchedulingCase, ProposedDecision

SYSTEM_PROMPT = """You are a scheduling assistant for a home-services company. Answer the customer using ONLY the supplied scheduling facts.
Rules:
1. Never state, offer or confirm a day/time that is not in available_slots or the existing appointment.
2. Report appointment and crew status exactly as given. Tentative or unknown is never "confirmed" and never a promise that the crew will attend.
3. A scheduling conflict exists only when another ACTIVE (scheduled/in_progress) job overlaps. Completed or cancelled jobs are not conflicts.
4. If the customer says they will get back to you, acknowledge and wait; do not propose a booking.
5. If critical facts are missing, say you need to verify and escalate. Never guess.
Answer in one or two short sentences. You propose; a separate policy validator checks your proposal.
Return ONLY JSON: {"action": "reply"|"wait"|"escalate", "reply": "<message to the customer>"}"""

FALLBACK = ProposedDecision(action="escalate", reply="We need to verify the scheduling details before confirming. A team member will review this request.")


def agent_facts(case: SchedulingCase) -> dict[str, Any]:
    """Exactly the facts shown to the agent (and recorded as evidence): no proposal, no expected outcome."""
    return case.model_dump(exclude={"proposed_decision", "expected", "category"})


def extract_decision(raw: str) -> ProposedDecision:
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("No JSON object in model response")
    return ProposedDecision.model_validate(json.loads(raw[a:b + 1]))


def make_agent(settings: Settings) -> Any:
    from strands import Agent
    from strands.models import BedrockModel
    model = BedrockModel(model_id=settings.model_id, region_name=settings.region,
                         temperature=settings.temperature, max_tokens=settings.max_tokens)
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None)


def live_propose(case: SchedulingCase, settings: Settings, agent: Any = None) -> tuple[ProposedDecision, str, str | None]:
    """Returns (decision, source, error). Any failure degrades to an escalation, never raw model text."""
    try:
        agent = agent or make_agent(settings)
        prompt = "Scheduling facts:\n" + json.dumps(agent_facts(case), indent=2) + "\n\nReturn only the JSON object."
        return extract_decision(str(agent(prompt))), "bedrock", None
    except Exception as exc:  # noqa: BLE001 - boundary: log and degrade
        print(f"live agent error: {type(exc).__name__}: {exc}")
        return FALLBACK, "bedrock-fallback", f"{type(exc).__name__}: {exc}"[:400]


def mock_propose(case: SchedulingCase) -> tuple[ProposedDecision, str]:
    """Mock mode: replay the fixture's simulated model output; otherwise a small deterministic agent."""
    if case.proposed_decision is not None:
        return case.proposed_decision, "fixture"
    msg = case.customer_message.casefold()
    if any(p in msg for p in ("i'll let you know", "i will let you know", "when i'm back", "when i am back")):
        return ProposedDecision(action="wait", reply="Thanks for letting us know. Please message us when you are back."), "mock-agent"
    if case.crew.confirmation_status != "confirmed" or case.appointment.status != "confirmed":
        return ProposedDecision(action="reply", reply="Your appointment is tentative and crew attendance is not yet confirmed. We will check and update you."), "mock-agent"
    return ProposedDecision(action="reply", reply="I will verify the current scheduling details before confirming."), "mock-agent"
