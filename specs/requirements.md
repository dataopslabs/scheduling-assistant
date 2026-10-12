# Requirements

Source: *Technical task: review an AI scheduling assistant* (4 synthetic cases A–D). Format: EARS.

## Problem
The assistant's instruction ("be helpful, be proactive, offer the next step") makes it sound helpful rather than be grounded, so it invents conflicts (A), pushes bookings against customer intent (B), invents availability (C) and overstates certainty (D).

## Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | WHEN a customer message and scheduling facts are submitted, THE SYSTEM SHALL obtain a proposed decision `{action: reply\|wait\|escalate, message, committed_slot_start}` from an LLM on Amazon Bedrock. |
| FR-2 | THE SYSTEM SHALL validate every proposed decision with deterministic code BEFORE it is returned to the customer. |
| FR-3 (Case C) | IF a decision commits to, or affirms, a time/day that is not an available slot or the existing appointment, THEN THE SYSTEM SHALL reject it and offer up to 3 real slots (or escalate if none). |
| FR-4 (Case D) | IF a decision states the crew will attend while crew confirmation is not `true`, or says "confirmed" while status ≠ confirmed, THEN THE SYSTEM SHALL reject it and state the true status and escalate. |
| FR-5 (Case A) | IF a decision claims a conflict/delay and no ACTIVE (scheduled/in_progress) job of the same crew overlaps the appointment, THEN THE SYSTEM SHALL reject it and answer from the appointment status instead of escalating. |
| FR-6 (Case B) | IF the customer says they will get back to us, THEN THE SYSTEM SHALL require `action = wait` with no booking push; otherwise replace with a short acknowledgement. |
| FR-7 | IF the model call fails or its output cannot be parsed, THEN THE SYSTEM SHALL escalate with a neutral holding message, never an unvetted model text. |
| FR-8 | THE SYSTEM SHALL return, for every request, the proposed decision, the guard verdict (accepted/blocked, rule, reason) and the final decision. |
| FR-9 | THE SYSTEM SHALL support the original and the improved instruction (selectable) and a "replay simulated decision" mode that needs no model call. |
| FR-10 | THE UI SHALL let a user pick scenarios A–D, edit facts, run the live agent or replay the original bad decision, toggle enforcement, and see proposed → verdict → final side by side. |

## Non-functional requirements
- NFR-1 Hard invariants are enforced in code (100%), tone/judgement in the instruction.
- NFR-2 Guard is pure Python, stdlib only, no I/O; unit-testable offline.
- NFR-3 Deployed on AWS: Lambda (Python 3.12) + HTTP API + Bedrock; UI on Amplify Hosting.
- NFR-4 Least privilege: Lambda may only `bedrock:InvokeModel`; CORS restricted to the Amplify origin; API throttled (5 rps / burst 10) because the endpoint is public and Bedrock is metered.
- NFR-5 Deploy is reproducible with one script and refuses to deploy when tests fail.
- NFR-6 p95 latency dominated by the model call (target < 5 s for a Haiku-class model).

## Out of scope
Real customer data, authentication/user accounts, persistence, calendar integration, multi-turn memory.

## Acceptance criteria
1. Each of the four original decisions is rejected, with a reason and an alternative that itself passes the guard.
2. For each case a valid decision is accepted.
3. UI replay of A–D shows BLOCKED and the safe reply; live run returns a guarded result.
4. `deploy.sh` yields a reachable API `/health` and an Amplify URL.
