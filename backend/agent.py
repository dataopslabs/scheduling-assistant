"""Scheduling agent: a Strands Agent (Amazon Bedrock model) proposes a decision, the safeguard validates it."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from safeguard import (Appointment, Job, ProposedDecision, SchedulingFacts, Slot, apply_guard)

PROMPTS = Path(__file__).parent / "prompts"
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

OUTPUT_FORMAT = (
    'Respond with JSON only, no prose: {"action": "reply"|"wait"|"escalate", "message": "<customer reply>", '
    '"committed_slot_start": "<ISO datetime>"|null}. committed_slot_start must be set whenever the '
    "message books or confirms a specific time."
)


def load_prompt(mode: str) -> str:
    if mode not in ("naive", "improved"):
        raise ValueError("prompt must be 'naive' or 'improved'")
    return (PROMPTS / f"{mode}.md").read_text().strip()


# ---- (de)serialisation -------------------------------------------------------------------
def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)


def parse_facts(p: dict[str, Any]) -> SchedulingFacts:
    appt = p.get("appointment")
    return SchedulingFacts(
        now=_dt(p["now"]),
        customer_message=str(p.get("customer_message", "")),
        available_slots=tuple(Slot(_dt(s["start"]), _dt(s["end"])) for s in p.get("available_slots", [])),
        appointment=Appointment(_dt(appt["start"]), _dt(appt["end"]), appt["status"],
                                appt.get("crew"), appt.get("crew_confirmed")) if appt else None,
        other_jobs=tuple(Job(_dt(j["start"]), _dt(j["end"]), j["crew"], j["status"])
                         for j in p.get("other_jobs", [])),
    )


def parse_decision(p: dict[str, Any]) -> ProposedDecision:
    action = p.get("action")
    if action not in ("reply", "wait", "escalate") or not isinstance(p.get("message"), str):
        raise ValueError("decision needs action in reply|wait|escalate and a string message")
    slot = p.get("committed_slot_start")
    return ProposedDecision(action, p["message"], _dt(slot) if slot else None)


def decision_to_dict(d: ProposedDecision) -> dict[str, Any]:
    return {"action": d.action, "message": d.message,
            "committed_slot_start": d.committed_slot_start.isoformat() if d.committed_slot_start else None}


def extract_json(text: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("model returned no JSON object")
    return json.loads(m.group(0))


# ---- Strands agent on Bedrock ------------------------------------------------------------
def make_agent(system: str, model_id: str = MODEL_ID) -> Any:
    from strands import Agent
    from strands.models import BedrockModel
    model = BedrockModel(model_id=model_id, temperature=0.0, max_tokens=400,
                         region_name=os.environ.get("AWS_REGION"))
    return Agent(model=model, system_prompt=system, callback_handler=None)  # no stdout streaming


def call_agent(system: str, facts_payload: dict[str, Any], agent: Any = None,
               model_id: str = MODEL_ID) -> ProposedDecision:
    agent = agent or make_agent(system, model_id)
    user = f"Scheduling facts:\n{json.dumps(facts_payload, indent=2)}\n\n{OUTPUT_FORMAT}"
    return parse_decision(extract_json(str(agent(user))))


# ---- orchestration -----------------------------------------------------------------------
def run(payload: dict[str, Any], agent: Any = None) -> dict[str, Any]:
    """payload: {facts, prompt: naive|improved, simulated_decision?, guard?: bool}"""
    facts = parse_facts(payload["facts"])
    mode = payload.get("prompt", "improved")
    source = "simulated" if payload.get("simulated_decision") else "strands-bedrock"
    try:
        proposed = (parse_decision(payload["simulated_decision"]) if source == "simulated"
                    else call_agent(load_prompt(mode), payload["facts"], agent))
    except Exception as exc:  # model/parse failure must never reach the customer unvetted
        return {"source": source, "prompt": mode, "error": f"{type(exc).__name__}: {exc}",
                "proposed": None, "guard": {"acceptable": False, "rule": "model_error",
                                            "reason": "Model call failed; escalating to a human."},
                "final": {"action": "escalate", "message": "Thanks — I've passed your request to our "
                          "scheduling team and they'll reply shortly.", "committed_slot_start": None}}
    final, verdict = apply_guard(facts, proposed) if payload.get("guard", True) else (
        proposed, apply_guard(facts, proposed)[1])
    return {
        "source": source, "prompt": mode, "model": MODEL_ID if source != "simulated" else None,
        "proposed": decision_to_dict(proposed),
        "guard": {"acceptable": verdict.acceptable, "rule": verdict.rule, "reason": verdict.reason,
                  "enforced": payload.get("guard", True)},
        "final": decision_to_dict(final),
    }
