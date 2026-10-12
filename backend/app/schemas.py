from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

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
    use_case: Optional[str] = None      # base use case (A-001) for synthetic dataset variants
    variant: Optional[int] = None
    title: Optional[str] = None
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


Intent = Literal["status_check", "crew_attendance", "availability_check", "booking_request", "defer_to_customer", "other"]
NextAction = Literal["answer_status", "offer_slots", "book_slot", "wait_for_customer", "escalate"]
Resolution = Literal["approved", "rewritten", "safe_response", "human_escalation"]


class DraftRequest(BaseModel):
    """Step 1 output (RequestReviewerAgent): the customer message as a structured draft request. No facts, no tools."""
    intent: Intent = "other"
    requested_day: Optional[str] = None
    requested_time: Optional[str] = None
    customer_will_followup: bool = False
    confirms_slot: bool = False           # customer explicitly agrees to a specific slot
    asks_crew_attendance: bool = False
    summary: str = ""

    @field_validator("intent", mode="before")
    @classmethod
    def _coerce_intent(cls, v):
        """Models sometimes invent labels. Map known aliases; anything else becomes 'other' (low confidence -> human)."""
        aliases = {"asks_crew_attendance": "crew_attendance", "crew": "crew_attendance", "attendance": "crew_attendance",
                   "confirm_slot": "booking_request", "book_slot": "booking_request", "book": "booking_request", "booking": "booking_request",
                   "availability": "availability_check", "check_availability": "availability_check", "status": "status_check",
                   "check_status": "status_check", "defer": "defer_to_customer", "wait": "defer_to_customer", "followup": "defer_to_customer"}
        v = str(v or "other").strip().lower()
        valid = {"status_check", "crew_attendance", "availability_check", "booking_request", "defer_to_customer", "other"}
        return v if v in valid else aliases.get(v, "other")


class Judgment(BaseModel):
    """Step 2 output (Strands Decider): typed judgment with confidence. Below the threshold a human takes over."""
    next_action: NextAction
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    flags: list[str] = Field(default_factory=list)


class SlotRecord(BaseModel):
    slot_id: str
    label: str
    date: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None


class JobRecord(BaseModel):
    job_id: str
    status: str
    active: bool


class BookingResult(BaseModel):
    slot_id: Optional[str] = None
    performed: bool
    dry_run: bool
    reason: str


class AppointmentRecord(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class RequestedSlot(BaseModel):
    day: Optional[str] = None
    time: Optional[str] = None
    matched_slot_id: Optional[str] = None


class EvidencePack(BaseModel):
    """Step 3 output (Python): the only facts the response writer and the final guard may rely on."""
    customer_message: str
    appointment: Optional[AppointmentRecord] = None
    crew_confirmation: Optional[str] = None
    available_slots: list[SlotRecord] = Field(default_factory=list)
    other_jobs: list[JobRecord] = Field(default_factory=list)
    active_jobs: list[str] = Field(default_factory=list)
    requested: RequestedSlot = Field(default_factory=RequestedSlot)
    booking: Optional[BookingResult] = None
    data_complete: bool = True
    missing: list[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    key: str
    name: str
    status: Literal["ok", "skipped", "error", "blocked"]
    detail: str = ""
    ms: int = 0


class DecideRequest(BaseModel):
    mode: Mode = "mock"
    case: SchedulingCase


class Evidence(BaseModel):
    request_id: str
    timestamp: str
    latency_ms: int
    mode: Mode
    source: str                 # fixture | mock-agent | bedrock | bedrock-fallback
    model_id: Optional[str] = None
    facts: dict                 # exactly what the agent / policy saw
    rules: list[RuleResult]
    error: Optional[str] = None
    pipeline: list[PipelineStep] = Field(default_factory=list)
    draft_request: Optional[DraftRequest] = None
    judgment: Optional[Judgment] = None
    evidence_pack: Optional[EvidencePack] = None
    rewrite_attempted: bool = False


class DecisionResponse(BaseModel):
    case_id: str
    mode: Mode
    proposed_decision: ProposedDecision
    acceptable: bool
    findings: list[PolicyFinding]
    final_action: Action
    final_reply: str
    resolution: Resolution = "approved"
    note: str
    evidence: Evidence


class BatchRequest(BaseModel):
    mode: Mode = "mock"
    use_case: Optional[str] = None                 # run every dataset of one use case ...
    case_ids: Optional[list[str]] = None           # ... or an explicit list of dataset ids


class BatchItem(BaseModel):
    case_id: str
    title: Optional[str] = None
    customer_message: str
    expected_acceptable: Optional[bool] = None
    decision: DecisionResponse


class BatchResponse(BaseModel):
    mode: Mode
    total: int
    approved: int
    blocked: int
    items: list[BatchItem]
