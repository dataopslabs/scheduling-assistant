# Scheduling assistant safeguard

Spec-driven build: `specs/requirements.md` → `specs/design.md` → `specs/tasks.md`. Review and improved instruction: `docs/REVIEW.md`.

**Model proposes, code disposes.** A Strands Agent (Amazon Bedrock model) proposes a reply/wait/escalate decision; deterministic safeguards for all four cases (A conflict, B deferral, C slot, D status) validate it before the customer sees it.

## Run tests (Python 3.9+, stdlib only)
```bash
PYTHONPATH=backend:tests python3 -m unittest discover -s tests -v
```

## Run locally without AWS
Tests use a fake Strands agent; the UI's "Replay original bad decision" button needs no model.

## Deploy (Lambda + Bedrock + Amplify)
Prereqs: AWS CLI (no SAM or Docker needed; pip fetches Linux wheels), credentials, and **Bedrock model access enabled** for the model in `BedrockModelId` (default `us.amazon.nova-lite-v1:0`; Anthropic models need AWS Marketplace permissions/billing, set `BedrockModelId` to use one) in your region.
```bash
AWS_REGION=us-east-1 ./deploy.sh
```
It runs tests, deploys the SAM stack (`infra/template.yaml`), creates/updates the Amplify app with a zip deployment of `frontend/` with `API_URL` injected, then locks CORS to the Amplify origin. Prints the UI URL.

Repo-connected Amplify instead: connect this repo in the console, set env var `API_URL` to the stack's `ApiUrl`; `amplify.yml` handles the rest.

## Limitations
- Not deployed or run against live Bedrock from this sandbox (no AWS access). Only the fake-client and local-handler paths are verified. Model ID and IAM need confirming in your account.
- The endpoint is public and unauthenticated (throttled to 5 rps); add auth before sharing widely.
- Text checks are regex heuristics (weekday/today/tomorrow only, English, no explicit dates, no time-of-day mismatch). Structured `committed_slot_start` is the real guarantee.
- Naive datetimes; no timezone handling.

## AI use
Built with Claude. Checked by reading the rules against the task, running the tests (original decisions fail, valid ones pass), validating the template with cfn-lint, and driving the UI in headless Chromium against the real handler. Extends the supplied `scheduling-safeguard` Case C solution to all four cases.

## CI/CD (`develop` branch)
Pushing to `develop` runs `.github/workflows/deploy.yml`, which calls `./deploy.sh`. One-time setup: create an IAM role trusting GitHub OIDC for this repo (permissions: CloudFormation, Lambda, API Gateway, IAM pass-role, S3, Amplify, Bedrock invoke) and store its ARN as repo secret `AWS_DEPLOY_ROLE_ARN`. Optional repo variable `AWS_REGION`.
