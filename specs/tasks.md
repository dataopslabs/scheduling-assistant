# Tasks

Status legend: ✅ done and verified · ⚠️ done, not verifiable in this sandbox · ⬜ not done

## Phase 1 — Review and instruction
- ✅ T1 Review cases A–D, root cause, improved instruction → `docs/REVIEW.md`, `backend/prompts/improved.md`

## Phase 2 — Safeguard (FR-3…FR-6)
- ✅ T2 Data model + Case C slot rule
- ✅ T3 Case D status rule
- ✅ T4 Case A conflict rule (active + overlapping + same crew)
- ✅ T5 Case B deferral rule
- ✅ T6 Unit tests: each original decision rejected, alternative passes, valid decision accepted, edge cases (29 tests in total)

## Phase 3 — Agent and API (FR-1, 2, 7, 8, 9)
- ✅ T7 `agent.py` Bedrock Converse + JSON parsing + failure-to-escalate (tested with a fake client)
- ✅ T8 `handler.py` HTTP adapter + tests
- ⚠️ T9 Live Bedrock call (needs AWS credentials and model access)

## Phase 4 — UI (FR-10)
- ✅ T10 Single-page UI; verified headless against the real handler via a local shim (A–D replay → BLOCKED + safe reply)

## Phase 5 — Infra and deploy (NFR-3…5)
- ✅ T11 SAM template (cfn-lint clean), IAM least privilege, CORS, throttling
- ✅ T12 `amplify.yml`, `deploy.sh` (syntax-checked)
- ⚠️ T13 Run `./deploy.sh` in the target AWS account, open UI, run all four cases live

## Phase 6 — Follow-ups (not started)
- ⬜ T14 Eval set: 30–50 paraphrases per case against the real model; measure JSON validity, `committed_slot_start` rate, guard precision/recall
- ⬜ T15 Auth (Cognito or API key) on the API; tz-aware datetimes; explicit-date parsing ("17 Oct"); time-of-day mismatch check
- ⬜ T16 Log guard rejections per model/prompt version (CloudWatch metric + alarm)
