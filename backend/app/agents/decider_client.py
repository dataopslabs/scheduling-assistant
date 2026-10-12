"""Strands Decider adapter: typed judgment of intent and next action, with a confidence score.
The Decider does not replace database checks and cannot book. Low confidence routes to a human."""
import json
from typing import Any, Optional
from ..config import Settings
from ..schemas import DraftRequest, EvidencePack, Judgment
from .llm import AgentSet, ask_typed, extract_json, resolve

SYSTEM_PROMPT = """You are the decision step of a guarded scheduling assistant. You receive a structured draft request (no scheduling facts).
Choose the next action:
- answer_status: customer asks about appointment/crew status
- offer_slots: customer asks about a day/time; verified slots will be offered
- book_slot: ONLY if the customer explicitly agreed to a specific day/time
- wait_for_customer: customer says they will get back to us (never propose a booking)
- escalate: unclear, risky or out of scope
Give an honest confidence between 0 and 1. If unsure, use a low confidence.
Return ONLY JSON: {"next_action": "...", "confidence": 0.0, "reason": "<short>"}"""

CLAIMS_PROMPT = """You audit a draft customer reply against an evidence pack. List every claim in the reply (date, time, slot, appointment status,
crew attendance, conflict, booking) that the evidence pack does NOT support. Return ONLY JSON: {"unsupported_claims": ["..."]}"""

_ACTION_BY_INTENT = {"status_check": "answer_status", "crew_attendance": "answer_status", "availability_check": "offer_slots",
                     "booking_request": "book_slot", "defer_to_customer": "wait_for_customer", "other": "escalate"}


def heuristic_decide(draft: DraftRequest) -> Judgment:
    """Deterministic decider used in mock mode: clear intents get high confidence, 'other' gets low."""
    action = _ACTION_BY_INTENT[draft.intent]
    if draft.customer_will_followup:
        action = "wait_for_customer"
    conf = 0.4 if draft.intent == "other" else 0.95
    return Judgment(next_action=action, confidence=conf, reason=f"mock decider: intent={draft.intent}")


def decide(draft: DraftRequest, message: str, live: bool, settings: Settings, agents: Optional[AgentSet] = None) -> Judgment:
    if not live:
        return heuristic_decide(draft)
    agent = resolve(agents.decider if agents else None, settings.decider_model_id, SYSTEM_PROMPT, settings)
    prompt = "Draft request:\n" + draft.model_dump_json(indent=2) + "\n\nReturn only the JSON object."
    return ask_typed(agent, prompt, Judgment)


def flag_unsupported_claims(reply: str, pack: EvidencePack, settings: Settings, agents: Optional[AgentSet] = None) -> list[str]:
    """Optional second opinion (live mode, DECIDER_REVIEW_CLAIMS=true). Flags only add to the deterministic guard, never override it."""
    agent = resolve(agents.decider if agents else None, settings.decider_model_id, CLAIMS_PROMPT, settings)
    prompt = "Evidence pack:\n" + pack.model_dump_json(indent=2) + "\n\nDraft reply:\n" + json.dumps(reply) + "\n\nReturn only the JSON object."
    return [str(x) for x in extract_json(str(agent(prompt))).get("unsupported_claims", [])]
