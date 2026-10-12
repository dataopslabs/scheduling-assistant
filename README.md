# Guarded Scheduling Agent

**AI proposes. The Decider judges. Python verifies. The system of record confirms.**

A customer-scheduling assistant built so that a plausible-sounding answer is never mistaken for a correct scheduling decision. LLMs interpret and communicate; deterministic Python verifies every fact and owns every scheduling write. Strands Agents + Amazon Bedrock, FastAPI on Lambda behind API Gateway, React/Vite on Amplify Hosting. **All data is synthetic; no real appointment is booked or modified.**

See the *About the project* page in the UI (Problem → Solution → Design diagrams in `docs/images/`).

## The pipeline

```
Customer message
  1 RequestReviewer (LLM)  message → structured draft request           no facts, no tools
  2 Strands Decider (LLM)  typed judgment + confidence                   < 0.9 → human review
  3 Python rules + tools   read verified facts, build EVIDENCE PACK,     the only component that can write
                           perform a write only for a customer-agreed available slot
  4 ResponseWriter (LLM)   reply from the evidence pack only             no tools
  5 Final response guard   validate every date / slot / status / crew / conflict / booking claim
                           fail → ONE rewrite → fail again → fixed safe response (escalate)
```

| Resolution | Meaning |
|---|---|
| `approved` | first draft passed the guard |
| `rewritten` | first draft failed; one rewrite from the evidence pack passed |
| `safe_response` | rewrite also failed; fixed safe reply sent, escalated |
| `human_escalation` | Decider confidence < threshold, action `escalate`, or an agent failed; customer gets a holding reply |

Security boundaries: LLMs cannot modify appointments · the Decider does not replace database checks · Python is the only component authorised to write · a booking needs the customer's agreement to a specific available slot · failed validation never silently bypasses the guard · any model error degrades to a human, never to raw model text.

## Code structure (`backend/app`)

```
main.py              app factory + Mangum Lambda handler          config.py   settings from env
schemas.py           request/response + DraftRequest, Judgment, EvidencePack, PipelineStep, ...
api/routes.py        /health /api/config /api/cases /api/datasets /api/decide /api/batch /api/evaluate
agents/              request_reviewer.py · decider_client.py · response_writer.py · llm.py (Strands/Bedrock helpers)
tools/scheduling_api.py     the only reader of the system of record and the only writer (dry-run by default)
services/            scheduling_service.py (orchestrator) · evidence_builder.py · response_guard.py · cases.py
policies/            availability_rules.py (E3) · conflict_rules.py (E1) · confirmation_rules.py (E4)
                     intent_rules.py (E2) · data_rules.py (E5) · base.py (RuleContext, vocabularies)
policy.py            thin compatibility wrapper over policies/
fixtures/            synthetic_cases.json (10 base use cases) · datasets.json (30 variants) · generate_datasets.py
backend/tests/       per-rule tests, guard, agents, tool layer, pipeline, API, datasets
```

### Policy rules
| Rule | Source case | Check |
|---|---|---|
| E1 conflict accuracy | A | a conflict claim needs an ACTIVE other job; completed/cancelled jobs are not conflicts |
| E2 customer intent | B | customer will update later ⇒ no booking push |
| E3 availability integrity | C | never affirm a weekday that has no slot (names or ISO dates) |
| E4 confirmation integrity | D | attendance promise needs crew `confirmed`; "confirmed" needs a confirmed appointment; "booked" needs a performed booking |
| E5 data uncertainty | – | missing/invalid status fails closed (other rules skipped) |

## Modes
- **Mock** (`mode: "mock"`): no model call. Deterministic reviewer/decider/writer; a fixture's recorded (possibly unsafe) model reply is replayed through the guard.
- **Live** (`mode: "live"`): three Strands agents on Bedrock (reviewer, decider, writer), then the same Python tools and guard. Default model `amazon.nova-pro-v1:0`.

## Configuration (env)
| Variable | Default | Purpose |
|---|---|---|
| `BEDROCK_MODEL_ID` | `amazon.nova-pro-v1:0` | model for all agent roles |
| `REVIEWER_MODEL_ID` / `DECIDER_MODEL_ID` / `WRITER_MODEL_ID` | = `BEDROCK_MODEL_ID` | per-role override (e.g. a smaller model for reviewer/writer) |
| `DECIDER_THRESHOLD` | `0.9` | minimum confidence to continue without a human |
| `DECIDER_REVIEW_CLAIMS` | `false` | extra LLM audit of the draft before the deterministic guard (one more call; can only add findings) |
| `SCHEDULING_WRITES_ENABLED` | `false` | demo is dry-run; when `true` the tool layer may perform a booking |
| `CORS_ORIGINS`, `AWS_REGION` | | API CORS, Bedrock region |

## Run locally
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
pytest -q                          # 168 tests, no AWS needed
python -m app.evaluation           # 10 base fixtures
python -m app.batch --mode mock    # all 30 datasets through the pipeline (writes docs/dataset-results-mock.*)
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173
```
Live mode needs AWS credentials with Bedrock access to the configured model(s): `python -m app.batch --mode live`.

## API
`GET /health` · `GET /api/config` · `GET /api/cases` · `GET /api/datasets[?use_case=]` · `POST /api/decide` `{"mode":"mock|live","case":{...}}` · `POST /api/batch` `{mode, use_case | case_ids}` (max 10) · `POST /api/evaluate`.

`/api/decide` returns the proposed draft, `final_reply`, `resolution`, `findings` and `evidence`: facts seen, per-rule results, **pipeline steps with timings**, draft request, Decider judgment (confidence), evidence pack, model, latency and any error.

## UI
Top bar: **About the project** (Problem · Solution · Design) and **Test lab**. The lab has three panels: use cases and datasets (left), conversation/response (middle), evidence (right: Facts · Pipeline · Policy · Trace · History) with a switch between **Test Mock Data** and **Test Live Agent (LLM)**.

## Deploy (not changed by the pipeline refactor)
`./deploy.sh` runs the tests, packages `backend/app` + `backend/fixtures` for Lambda, deploys CloudFormation (HTTP API + Lambda), builds and zip-deploys the React app to Amplify, and locks CORS. Pushing to `staging` runs `.github/workflows/deploy.yml` (needs `AWS_DEPLOY_ROLE_ARN`). A live request now makes three model calls (reviewer, decider, writer) plus up to one rewrite, so expect roughly 3–5 s warm; the API Gateway limit is 29 s.

## Status vs the target design
Implemented: all five pipeline stages, typed JSON judgments with the 0.9 gate, evidence pack, one-rewrite loop, safe response / human escalation, guarded tool layer with dry-run booking, per-role models, automated tests.
Not implemented: a real scheduling API / appointment database (the tool layer is backed by the synthetic case), a real human-agent queue (escalation returns a holding reply), Amazon Bedrock AgentCore Runtime hosting, authentication and rate limiting beyond API Gateway throttling.

## Limitations
- Rule checks are heuristics over text (weekday/today/tomorrow, English); explicit calendar dates ("October 19th") and paraphrased promises can slip through. The evidence pack and typed judgments reduce, not remove, that risk.
- The Decider's confidence is self-reported by the model; the gate is only as good as its calibration. Validate against a labelled set before trusting 0.9.
- Conflict detection treats any active job as potentially conflicting (job times are not compared).
- `docs/dataset-results-live.*` were produced by the earlier single-agent version; run `python -m app.batch --mode live` to refresh them for the pipeline (a live request makes 3 model calls, so a full batch takes a few minutes).
- In live runs the Decider usually reports confidence of exactly 0.90–1.00, so the 0.9 gate rarely fires on clear messages; it mainly catches low-confidence outputs and failures.
- Before production: typed slot IDs end to end, adversarial test corpora, human review queue, auth, observability, audit retention, idempotency and concurrency control on writes.
