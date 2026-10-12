# Design

Guarded scheduling agent: **AI proposes. The Decider judges. Python verifies. The system of record confirms.**

```
Browser (Amplify, React) -> API Gateway HTTP API -> Lambda (FastAPI via Mangum)
  /api/decide {mode: mock|live}
    1 request_reviewer   message -> DraftRequest                         (LLM; mock = heuristic)
    2 decider_client     DraftRequest -> Judgment{next_action, confidence}  (LLM; < 0.9 -> human)
    3 tools + evidence   SchedulingAPI reads -> EvidencePack; guarded book_slot (Python only)
    4 response_writer    EvidencePack -> reply                           (LLM; mock = templates / recorded reply)
    5 response_guard     policies E1-E5 vs EvidencePack; one rewrite; safe response; or human
```

## Modules
`agents/` (no tools) · `tools/scheduling_api.py` (reads + guarded writes, dry-run by default) · `services/evidence_builder.py` ·
`services/response_guard.py` · `services/scheduling_service.py` (orchestration, pipeline trace) · `policies/` (one module per rule family).

## Decisions
- Each LLM role returns typed JSON validated by pydantic; invalid output is an error, never trusted text.
- Any agent failure or low confidence yields `human_escalation` with a fixed holding reply.
- The writer and the guard see only the evidence pack. Reviewer and decider never see scheduling facts.
- A write happens only in the tool layer, only for a customer-agreed slot that is still available, and is dry-run unless `SCHEDULING_WRITES_ENABLED=true`.
- Mock mode keeps the demo reproducible: recorded unsafe replies are replayed through the same guard, rewrite and safe-response logic.
- Per-role model IDs allow smaller models for reviewer/writer; default is one model (`amazon.nova-pro-v1:0`).

## Failure modes
Model/IAM error, invalid JSON, low confidence -> human escalation (error recorded in evidence). Failed guard -> one rewrite -> fixed safe response. Missing facts -> E5 fail-closed.
