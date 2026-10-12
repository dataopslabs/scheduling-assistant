import json
import pytest
from app.agents import llm


class FakeLLM:
    """Stands in for a Strands Agent: callable(prompt) -> text. Records prompts."""
    def __init__(self, reply): self.reply, self.prompts = reply, []
    def __call__(self, prompt):
        self.prompts.append(prompt)
        r = self.reply.pop(0) if isinstance(self.reply, list) else self.reply   # a list = one reply per call
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)


ROLE_MARKERS = {"reviewer": "convert a customer's message", "decider": "decision step", "writer": "write the customer-facing reply"}


@pytest.fixture
def fake_llm(monkeypatch):
    """fake_llm(reviewer=..., decider=..., writer=...) patches the agent factory; returns {role: FakeLLM}."""
    def install(reviewer=None, decider=None, writer=None):
        fakes = {"reviewer": FakeLLM(reviewer if reviewer is not None else {"intent": "availability_check", "requested_day": "saturday", "summary": "x"}),
                 "decider": FakeLLM(decider if decider is not None else {"next_action": "offer_slots", "confidence": 0.95, "reason": "x"}),
                 "writer": FakeLLM(writer if writer is not None else {"action": "reply", "reply": "ok"})}
        def factory(model_id, system_prompt, settings):
            for role, marker in ROLE_MARKERS.items():
                if marker in system_prompt:
                    return fakes[role]
            raise AssertionError("unexpected agent role: " + system_prompt[:60])
        monkeypatch.setattr(llm, "make_agent", factory)
        return fakes
    return install
