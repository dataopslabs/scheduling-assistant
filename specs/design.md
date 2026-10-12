# Design

## Architecture
```
Browser (Amplify Hosting, static index.html + config.js)
   │  POST /decide  {facts, prompt, guard, simulated_decision?}
   ▼
API Gateway HTTP API (CORS = Amplify origin, throttled)
   ▼
Lambda  handler.py ─► agent.run()
                         ├─ prompts/{naive,improved}.md  (system instruction)
                         ├─ Strands Agent (BedrockModel, temp 0, JSON-only output)   ← unless simulated_decision
                         └─ safeguard.apply_guard()  (deterministic rules C → D → A → B)
   ◄─ {proposed, guard{acceptable,rule,reason}, final}
```
**Model proposes, code disposes.** The LLM output is untrusted input to a validator; only the validator's result can reach the customer.

## Components
| Path | Responsibility |
|---|---|
| `backend/safeguard.py` | Data model (`SchedulingFacts`, `Appointment`, `Job`, `Slot`, `ProposedDecision`), four rules, `check_decision`, `apply_guard`, safer alternatives. Stdlib only. |
| `backend/agent.py` | JSON ⇄ dataclasses, Bedrock `converse` call, JSON extraction, orchestration, failure → escalate. |
| `backend/handler.py` | HTTP adapter: `POST /decide`, `GET /health`, 400 on malformed input. |
| `backend/prompts/*.md` | Original and improved instruction (the improved one is the deliverable of the review). |
| `frontend/` | Single-page UI, no build step; `config.js` carries `API_URL`. |
| `infra/template.yaml` | SAM: function, HTTP API, IAM, CORS, throttling; output `ApiUrl`. |
| `amplify.yml`, `deploy.sh` | Amplify build spec (repo-connected) and the CLI end-to-end deploy. |

## Safeguard rules
| Rule | Case | Check | Alternative |
|---|---|---|---|
| `slot` | C | `committed_slot_start` ∈ available starts ∪ appointment; affirmative, non-negated sentences naming a day (today/tomorrow/weekday) resolve to a date with a slot or the appointment | decline + ≤3 real slots, or escalate if none |
| `status` | D | crew-arrival promise needs `crew_confirmed is True`; "confirmed" needs `status == confirmed`; sentences with uncertainty words (tentative, not, yet, once…) are exempt | state tentative/unconfirmed, escalate |
| `conflict` | A | conflict/delay claim needs same-crew job, status ∈ {scheduled, in_progress}, intervals overlap | confirm appointment, no escalation |
| `deferral` | B | customer matches "I'll let you know / when I'm back / away" ⇒ `action == wait` and no `?`/book/schedule wording | "message us when you're back" (wait) |

Structured field is the primary guarantee (exact match); text scanning is defence in depth.

## Code vs instruction
Both. Instruction lowers violation rate and handles judgement (A, B tone). Code gives the guarantee for invariants (C, D) and logs violations. The model is asked for a machine-checkable `committed_slot_start` for that reason.

## Key decisions
- **Strands Agents SDK** (`strands-agents`, packaged via `backend/requirements.txt`; `sam build --use-container`) with an inference-profile ID parameter, temperature 0.
- **HTTP API over Function URL**: native throttling and CORS config. No auth (demo); noted as a risk.
- **Amplify manual deploy** from the script (no GitHub OAuth needed); `amplify.yml` supports repo-connected CI/CD as well.
- **Timezone-naive** datetimes for the demo; production should use tz-aware values.

## Failure modes
Bedrock throttling/AccessDenied/invalid JSON → `model_error` → escalate with holding message. Malformed request → 400. Regex miss → structured field still protects slots.
