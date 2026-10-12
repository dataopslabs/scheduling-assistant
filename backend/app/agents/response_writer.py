"""Response writer (small LLM): writes the customer reply using ONLY the evidence pack. No scheduling tools.
Mock mode uses deterministic templates built from the pack (also used as the safe rewrite)."""
import json
from typing import Any, Optional
from ..config import Settings
from ..policies.base import slot_days
from ..schemas import DraftRequest, EvidencePack, Judgment, PolicyFinding, ProposedDecision
from .llm import AgentSet, ask_typed, resolve

SYSTEM_PROMPT = """You write the customer-facing reply for a home-services scheduler using ONLY the evidence pack you are given.
Rules:
- Never state or offer a day/time that is not in available_slots or the existing appointment.
- Report appointment and crew status exactly as in the pack. Tentative/unknown/pending is never "confirmed" and never a promise the crew will attend.
- Mention a conflict only if active_jobs is non-empty. Completed or cancelled jobs are not conflicts.
- Say a booking was made only if booking.performed is true. If booking.dry_run is true, say the team will confirm it.
- If the customer said they will get back to us, acknowledge and wait. Do not propose a booking.
- If data_complete is false, say you need to verify and escalate.
Keep it to one or two short sentences. Return ONLY JSON: {"action": "reply|wait|escalate", "reply": "<message>"}"""

HOLDING = ProposedDecision(action="escalate", reply="Thanks - I've passed your request to our scheduling team and they'll reply shortly.")


def _when(pack: EvidencePack) -> str:
    a = pack.appointment
    if not a:
        return "your appointment"
    span = f"{a.start_time}–{a.end_time}" if a.start_time and a.end_time else (a.start_time or "")
    return f"your appointment on {a.date} {span}".strip()


def template_write(pack: EvidencePack, judgment: Judgment, draft: DraftRequest) -> ProposedDecision:
    """Deterministic reply from verified evidence only."""
    if not pack.data_complete:
        return ProposedDecision(action="escalate", reply="We need to verify the appointment and crew status before confirming.")
    act = judgment.next_action
    if act == "wait_for_customer":
        return ProposedDecision(action="wait", reply="Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment.")
    if act == "book_slot" and pack.booking:
        label = next((s.label for s in pack.available_slots if s.slot_id == pack.booking.slot_id), "that slot")
        if pack.booking.performed:
            return ProposedDecision(action="reply", reply=f"Thank you. {label} is now booked.")
        return ProposedDecision(action="escalate", reply=f"Thank you. I've requested {label} for you and our team will confirm it shortly.")
    if act in ("offer_slots", "book_slot"):
        day = (pack.requested.day or "").casefold()
        labels = [s.label for s in pack.available_slots][:3]
        matched = next((s for s in pack.available_slots if s.slot_id == pack.requested.matched_slot_id), None)
        if matched:
            return ProposedDecision(action="reply", reply=f"{matched.label} is available. Would you like to proceed?")
        if not labels:
            return ProposedDecision(action="escalate", reply=f"Sorry, we don't have {day.capitalize() + ' ' if day else ''}availability right now. I've asked our scheduling team to find you a time.")
        lead = f"Sorry, we don't have {day.capitalize()} availability. " if day and day not in slot_days([{"day": s.day, "date": s.date} for s in pack.available_slots]) else ""
        return ProposedDecision(action="reply", reply=f"{lead}We can offer: {' or '.join(labels)}. Would one of those work?")
    if act == "answer_status":
        a, crew = pack.appointment, (pack.crew_confirmation or "")
        if a is None or (a.status or "") == "none":
            return ProposedDecision(action="reply", reply="We don't have an appointment on record for you yet. Would you like to see the available times?")
        if a.status in ("cancelled", "completed"):
            return ProposedDecision(action="reply", reply=f"Our records show {_when(pack)} as {a.status}.")
        if a.status == "confirmed" and (not draft.asks_crew_attendance or crew == "confirmed"):
            extra = " The crew is confirmed." if crew == "confirmed" else ""
            return ProposedDecision(action="reply", reply=f"Yes — {_when(pack)} is confirmed.{extra}")
        return ProposedDecision(action="escalate", reply=f"{_when(pack).capitalize()} is {a.status} and crew attendance is not yet confirmed. We'll check and update you.")
    return HOLDING


def write(pack: EvidencePack, judgment: Judgment, draft: DraftRequest, live: bool, settings: Settings,
          agents: Optional[AgentSet] = None, violations: Optional[list[PolicyFinding]] = None) -> ProposedDecision:
    """First draft (violations=None) or one rewrite that is told which claims were rejected."""
    if not live:
        return template_write(pack, judgment, draft)
    agent = resolve(agents.writer if agents else None, settings.writer_model_id, SYSTEM_PROMPT, settings)
    prompt = "Evidence pack:\n" + pack.model_dump_json(indent=2) + "\n\nNext action decided: " + judgment.next_action
    if violations:
        prompt += "\n\nYour previous reply was REJECTED:\n" + "\n".join(f"- {v.reason}" for v in violations) + "\nRewrite it using only the evidence pack."
    return ask_typed(agent, prompt + "\n\nReturn only the JSON object.", ProposedDecision)
