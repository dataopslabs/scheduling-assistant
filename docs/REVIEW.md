# Review: AI scheduling assistant

The common root cause across all four cases: the current instruction ("be proactive and offer the next step") rewards *sounding* helpful over being *grounded*. The model fills gaps with confident guesses — inventing conflicts, inventing availability, inventing confirmation, and pushing a booking the customer didn't ask for.

## Case-by-case

| Case | What went wrong | Better decision |
|---|---|---|
| **A** – "Is my installation still happening tomorrow?" | **False positive / alarming.** The model saw the same crew on another job tomorrow and called it a conflict, ignoring that the other job is *completed*. A completed job cannot conflict. Escalating also creates internal noise and needlessly worries the customer. | **Reply:** "Yes — your installation is confirmed for tomorrow, 09:00–12:00." No escalation. Only treat overlapping *active* (scheduled/in-progress) jobs with time overlap as conflicts. |
| **B** – "I'm away from home. I'll let you know when I'm back." | **Ignores an explicit customer signal.** The customer said they will initiate contact; pushing "tomorrow morning" contradicts that (they're away) and is pushy. "Be proactive" caused it. | **Wait** (no booking push). Optionally a short acknowledgement: "No problem — just message us when you're back and we'll find a time that suits you." No follow-up scheduled unless policy defines one. |
| **C** – "Can you come this Saturday?" (slots: Mon 10:00, Tue 14:00 only) | **Hallucinated availability — a commitment the business cannot keep.** Highest-impact error: it produces a no-show, a broken promise and a complaint. | **Reply:** "Sorry, we don't have Saturday availability. The next open slots are Monday 10:00 or Tuesday 14:00 — would either work?" Never confirm a time not in the supplied slots. **(Implemented in code.)** |
| **D** – "Is the crew coming tomorrow?" (tentative; crew confirmation unknown) | **Overstated certainty.** "Yes, the crew will be there" upgrades *tentative + unknown* to *confirmed*. If the crew doesn't come, trust is lost. | **Reply** stating the true status: "Your appointment tomorrow is tentative and the crew hasn't been confirmed yet. I'll let you know as soon as it is." Plus **escalate / create an internal task** to get crew confirmation, since the customer is waiting on it. |

### Why I implemented Case C
It's the case where a wrong answer creates a **customer-facing commitment** the business can't meet, and it's the most **deterministically checkable**: the allowed slots are an explicit list, so code can verify the claim exactly. Case D is a close second (status-vs-claim check); Cases A and B are more about reasoning/judgment and are better addressed in instructions plus evals.

## Improved assistant instruction

```
You are a scheduling assistant for a home-services company. You answer customer
questions using ONLY the scheduling facts supplied with each message.

Grounding rules
1. Never state, offer, or confirm a date or time that is not in the supplied
   available slots or existing appointments.
2. Report appointment status exactly as given. "Tentative" or "unknown" must never
   be described as confirmed. If something is unknown, say so and say what happens next.
3. A scheduling conflict exists only when two ACTIVE jobs (not completed or cancelled)
   for the same crew overlap in time. Do not escalate otherwise.
4. If the facts you need are missing or contradictory, do not guess: escalate.

Customer intent
5. Answer the question asked first, in one or two short sentences.
6. Respect what the customer says about timing. If they say they will get back to
   you, acknowledge it and choose "wait"; do not push a booking.
7. If a requested time is unavailable, say so plainly and offer up to three real
   alternatives from the available slots.

Actions
- reply: you can answer fully from the facts.
- wait: the customer will come back to you, or nothing is needed now.
- escalate: a human must act (real conflict, missing/contradictory data,
  unconfirmed crew the customer is relying on, or a request outside policy).

Output JSON: {"action": ..., "message": ..., "committed_slot_start": <ISO time or null>,
"facts_used": [...]}. committed_slot_start must be set whenever the message books
or confirms a specific time.
```

The structured output (`committed_slot_start`, `facts_used`) is deliberate: it makes the model's claims machine-checkable so code can enforce what the prompt only asks for.

## Code, instructions, or both? — Both
- **Instructions** reduce how often the model makes the mistake and shape tone, alternatives and intent handling (cases A and B are mostly judgment and live here).
- **Code** is the guarantee for hard invariants. "Never commit to a slot that doesn't exist" must hold 100% of the time; a prompt is probabilistic, so a deterministic check runs on every output before it reaches the customer. On failure it substitutes a safe, factual reply (or escalates when there are no slots) and the event can be logged to measure how often the model violates the rule.
