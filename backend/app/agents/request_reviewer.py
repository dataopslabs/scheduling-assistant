"""RequestReviewerAgent (small LLM): reads the customer message and produces a structured draft request.
It sees ONLY the message. It has no tools and no access to scheduling facts."""
import json
import re
from typing import Any, Optional
from ..config import Settings
from ..policies.intent_rules import DEFER
from ..schemas import DraftRequest
from .llm import AgentSet, ask_typed, resolve

SYSTEM_PROMPT = """You convert a customer's message into a structured request for a home-services scheduler.
You see ONLY the message. Do not answer the customer and do not assume any facts.
Return ONLY JSON:
{"intent": "status_check|crew_attendance|availability_check|booking_request|defer_to_customer|other",
 "requested_day": "<weekday name, 'today', 'tomorrow' or null>",
 "requested_time": "<HH:MM or null>",
 "customer_will_followup": <true if the customer says they will get back to us / let us know later>,
 "confirms_slot": <true only if the customer explicitly agrees to book a specific day/time>,
 "asks_crew_attendance": <true if asking whether the crew/team/someone is coming>,
 "summary": "<one short sentence>"}"""

_DAY = re.compile(r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")
_TIME = re.compile(r"\b(\d{1,2}:\d{2})\b")
_ATTEND = re.compile(r"\b(crew|team|fitters?|technicians?|installers?)\b.*\b(coming|turn up|arrive|be there|show up)\b|\b(someone|somebody)\b.*\b(coming|turn up|arrive|be there|show up)\b")
_STATUS = re.compile(r"\b(confirm\w*|still|verify|appointment|booking|booked|happening|happen|problems?|installation|status|on for)\b")
_AVAIL = re.compile(r"\b(come|visit|possible|free|available|availability|slot|chance)\b")
_AGREE = re.compile(r"\b(yes|ok|okay|sure|go ahead|please book|book it|that works|works for me|let's do)\b")


def message_confirms_slot(message: str) -> bool:
    """Deterministic check that the customer explicitly agreed to book a specific day. Python, not the LLM, authorises writes."""
    m = message.casefold()
    return bool(_AGREE.search(m) and _DAY.search(m) and re.search(r"\bbook\w*\b", m))


def heuristic_extract(message: str) -> DraftRequest:
    """Deterministic extractor used in mock mode (no model call)."""
    m = message.casefold()
    day, time = (_DAY.search(m).group(1) if _DAY.search(m) else None), (_TIME.search(m).group(1) if _TIME.search(m) else None)
    base = dict(requested_day=day, requested_time=time, summary=message[:120])
    if DEFER.search(m):
        return DraftRequest(intent="defer_to_customer", customer_will_followup=True, **base)
    if _AGREE.search(m) and day and "book" in m:
        return DraftRequest(intent="booking_request", confirms_slot=True, **base)
    if _ATTEND.search(m):
        return DraftRequest(intent="crew_attendance", asks_crew_attendance=True, **base)
    if _STATUS.search(m):
        return DraftRequest(intent="status_check", **base)
    if _AVAIL.search(m) or day:
        return DraftRequest(intent="availability_check", **base)
    return DraftRequest(intent="other", **base)


def extract_request(message: str, live: bool, settings: Settings, agents: Optional[AgentSet] = None) -> DraftRequest:
    if not live:
        return heuristic_extract(message)
    agent = resolve(agents.reviewer if agents else None, settings.reviewer_model_id, SYSTEM_PROMPT, settings)
    return ask_typed(agent, "Customer message:\n" + json.dumps(message) + "\n\nReturn only the JSON object.", DraftRequest)
