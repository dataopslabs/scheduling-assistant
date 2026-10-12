# AI Scheduling Reliability Platform

Strands Agents + Amazon Bedrock, FastAPI on Lambda, React/Vite on Amplify Hosting, deterministic policy validation and a five-category evaluation. **All data is synthetic; no real appointment is booked.** Spec: `specs/`. Case review: `docs/REVIEW.md`.

**Model proposes, policy disposes.** The agent only proposes `{action, reply}`; `backend/app/policy.py` validates it and the API returns the safe final reply.

| Rule | Source case | Check |
|---|---|---|
| E1 conflict accuracy | A | a conflict claim needs an ACTIVE other job (completed/cancelled cannot conflict) |
| E2 customer intent | B | customer says they will update later ⇒ no booking push |
| E3 availability integrity | C | never affirm a weekday that has no slot (weekday names or ISO dates) |
| E4 confirmation integrity | D | attendance promise needs crew `confirmed`; "confirmed" needs appointment confirmed |
| E5 data uncertainty (extension) | – | missing/invalid status fails closed |

## UI (three panels)
**Use cases** (left) → **Response** (middle) → **Evidence** (right: Facts, Policy, Trace, History). The top switch selects **Test Mock Data** (replays each fixture's simulated model output, no model call) or **Test Live Agent (LLM)** (Strands agent on Amazon Bedrock, default `amazon.nova-pro-v1:0`). A *Custom scenario* lets you write a customer message, set the facts and, in mock mode, the simulated reply to test the policy.

## Backend layout (`backend/app`)
`main.py` (app factory + Mangum `handler`) · `api/routes.py` · `config.py` (settings from env) · `schemas.py` · `policy.py` (rules E1–E5, per-rule results) · `services/{agent,decision,cases}.py`.

## Run locally
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
pytest -q && python -m app.evaluation
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173
```
Mock mode needs no AWS. Live mode needs AWS credentials with Bedrock access to `BEDROCK_MODEL_ID`.

## Deploy (API Gateway + Lambda + Bedrock + Amplify) — branch `staging`
```bash
export AWS_REGION=us-east-1 MODEL_ID=amazon.nova-pro-v1:0
./deploy.sh        # tests → Lambda package → CloudFormation (HTTP API + Lambda) → React build → Amplify zip deploy → CORS lock
```
Needs AWS CLI, Python 3, Node 20+, credentials (no SAM/Docker). Pushing to `staging` runs `.github/workflows/deploy.yml` (secret `AWS_DEPLOY_ROLE_ARN`, OIDC; optional var `BEDROCK_MODEL_ID`).

## API
`GET /health`, `GET /api/config`, `GET /api/cases`, `POST /api/decide` body `{"mode":"mock|live","case":{...}}` → decision + `evidence` (facts seen, per-rule results, model, latency, source), `POST /api/evaluate`.

## Limitations
- Public, unauthenticated, throttled (5 rps) API: add auth before wider sharing.
- Phrase checks are heuristics: no explicit-date parsing ("October 19th" vs weekday), paraphrase and negation gaps. Metrics are on synthetic fixtures, not live-LLM quality.
- Live model quality varies: a small model can answer weakly (Nova Lite answered C-001 with a non-answer) ("checking my schedule"); the policy accepts it because it makes no false promise, but it is unhelpful. Evaluate the chosen model on paraphrased cases before relying on it.
- Before production: typed slot IDs, structured claims, adversarial corpora, human review, auth, observability, audit retention, idempotency; verify blocked proposals can never reach write APIs.

## Changes vs the uploaded reference
Added: Mangum Lambda entry point, CloudFormation + deploy script, Strands model mapping via `BEDROCK_MODEL_ID` (the original `Agent()` ignored it), generalised policy rules + 11 tests, live-agent button, missing `vite-env.d.ts` (original frontend did not build), docs page served from the app.
