# Draft acceptance criteria (Verify step grades against these)

A draft reply is valid only if ALL hold:

1. Addresses the sender by name if a name is present in the email.
2. States only services within the six ECS service domains — no promises outside them.
3. Correct pricing: initial 30-min consultation is free; no other prices quoted unless present in memory context.
4. Contains exactly one clear next step (confirm a time slot / booking link).
5. Professional tone; no invented facts (dates, people, capabilities not in the inquiry or memory).
6. Signed as Drago, Booking Assistant, Edmund Cloud Solutions.

Verify is deterministic-first (rules 1, 3, 6 are string checks), model-graded second
(rules 2, 4, 5 via a cheap Qwen grading call). Any failure → forced retry, max 2 retries,
then escalate to human with the failure reasons attached.
