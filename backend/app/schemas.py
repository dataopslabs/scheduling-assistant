from typing import Literal, Optional
from pydantic import BaseModel, Field

Action = Literal["reply", "wait", "escalate"]
Mode = Literal["mock", "live"]


class Appointment(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class Crew(BaseModel):
    confirmation_status: Optional[str] = None


class ProposedDecision(BaseModel):
    action: Action = "reply"
    reply: str = Field(min_length=1, max_length=2000)


class SchedulingCase(BaseModel):
    case_id: str = "CUSTOM"
    category: str = "custom"
    customer_message: str = Field(min_length=1, max_length=1000)
    appointment: Appointment = Field(default_factory=Appointment)
    crew: Crew = Field(default_factory=Crew)
    available_slots: list[dict] = Field(default_factory=list)
    other_jobs: list[dict] = Field(default_factory=list)
    proposed_decision: Optional[ProposedDecision] = None
    expected: Optional[dict] = None


class PolicyFinding(BaseModel):
    rule_id: str
    severity: Literal["block", "review"] = "block"
    reason: str
    safer_alternative: str


class RuleResult(BaseModel):
    rule_id: str
    name: str
    status: Literal["passed", "blocked", "skipped"]
    reason: Optional[str] = None


class DecideRequest(BaseModel):
    mode: Mode = "mock"
    case: SchedulingCase


class Evidence(BaseModel):
    request_id: str
    timestamp: str
    latency_ms: int
    mode: Mode
    source: str                 # fixture | simulated | mock-agent | bedrock | bedrock-fallback
    model_id: Optional[str] = None
    facts: dict                 # exactly what the agent / policy saw
    rules: list[RuleResult]
    error: Optional[str] = None


class DecisionResponse(BaseModel):
    case_id: str
    mode: Mode
    proposed_decision: ProposedDecision
    acceptable: bool
    findings: list[PolicyFinding]
    final_action: Action
    final_reply: str
    note: str
    evidence: Evidence
