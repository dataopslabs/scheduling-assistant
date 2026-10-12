"""Thin Strands/Bedrock helpers shared by the agents. Agent objects are callables returning text, so tests inject fakes."""
import json
from dataclasses import dataclass
from typing import Any, Optional
from pydantic import BaseModel
from ..config import Settings


@dataclass
class AgentSet:
    """Optional injected agents (tests). None means: build a real Strands agent on Bedrock."""
    reviewer: Any = None
    decider: Any = None
    writer: Any = None


def make_agent(model_id: str, system_prompt: str, settings: Settings) -> Any:
    from strands import Agent
    from strands.models import BedrockModel
    model = BedrockModel(model_id=model_id, region_name=settings.region, temperature=settings.temperature, max_tokens=settings.max_tokens)
    return Agent(model=model, system_prompt=system_prompt, callback_handler=None)  # no tools attached


def extract_json(raw: str) -> dict:
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("No JSON object in model response")
    return json.loads(raw[a:b + 1])


def ask_typed(agent: Any, prompt: str, model: type[BaseModel]) -> Any:
    """Ask the agent and validate its JSON against a pydantic model (typed output; raises on anything else)."""
    return model.model_validate(extract_json(str(agent(prompt))))


def resolve(agent: Optional[Any], model_id: str, system_prompt: str, settings: Settings) -> Any:
    return agent if agent is not None else make_agent(model_id, system_prompt, settings)
