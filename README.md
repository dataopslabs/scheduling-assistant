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

## Run locally
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
pytest -q && python -m app.evaluation
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173
```
`AGENT_MODE=mock` (default) needs no AWS. `AGENT_MODE=bedrock` uses a Strands `Agent` with `BedrockModel(model_id=$BEDROCK_MODEL_ID)`.

## Deploy (Lambda + Bedrock + Amplify) — branch `staging`
```bash
export AWS_REGION=us-east-1 MODEL_ID=<bedrock model or inference-profile id>
./deploy.sh        # tests → Lambda package → CloudFormation → React build → Amplify zip deploy → CORS lock
```
Needs AWS CLI, Python 3, Node 20+, credentials, and Bedrock access to the model (no SAM/Docker). Default model `us.anthropic.claude-sonnet-5-5`, which requires a valid payment method/AWS Marketplace access in the account (otherwise Bedrock returns INVALID_PAYMENT_INSTRUMENT and the agent escalates). Non-Anthropic fallback that works without it: `us.amazon.nova-lite-v1:0`. Pushing to `staging` runs `.github/workflows/deploy.yml` (needs secret `AWS_DEPLOY_ROLE_ARN`, OIDC role; optional var `BEDROCK_MODEL_ID`).

## API
`GET /health`, `GET /api/cases`, `POST /api/decide` (omit `proposed_decision` to ask the live agent), `POST /api/evaluate`, `GET /api/report`.

## Case 1 - Solution 

You can call the Scheduling API via Programatically - Currently I mocked the available Slot
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/5f0ca145-3524-4845-9f1e-d998c1adcbea" />


## Limitations
- Public, unauthenticated, throttled (5 rps) API: add auth before wider sharing.
- Phrase checks are heuristics: no explicit-date parsing ("October 19th" vs weekday), paraphrase and negation gaps. Metrics are on synthetic fixtures, not live-LLM quality.
- Live model quality varies: a small model (Nova Lite) answered C-001 with a non-answer ("checking my schedule"); the policy accepts it because it makes no false promise, but it is unhelpful. Evaluate the chosen model on paraphrased cases before relying on it.
- Before production: typed slot IDs, structured claims, adversarial corpora, human review, auth, observability, audit retention, idempotency; verify blocked proposals can never reach write APIs.

## Changes vs the uploaded reference
Added: Mangum Lambda entry point, CloudFormation + deploy script, Strands model mapping via `BEDROCK_MODEL_ID` (the original `Agent()` ignored it), generalised policy rules + 11 tests, live-agent button, missing `vite-env.d.ts` (original frontend did not build), docs page served from the app.
