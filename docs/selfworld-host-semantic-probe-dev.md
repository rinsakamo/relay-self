# SelfWorld host-bound semantic projection DEV

Preregistration (unchanged): https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6364340813

The experiment reuses strict saved-source replay, its ATT/PRD verification,
`build_real_case` and the four original synthetic fixtures. The host-only frozen
manifest retains complete replay receipts, raw identities, ATT, prediction review,
typed RAW/SEM requests, both rendered BOUNDED/THINK payloads and their SHA256.
SEM uses fixed DEV request/provenance values with no source authority. It is
never imported as a World observation, Action source, Memory or learned fact.

Only request_id and context differ. SEM allowlists probe status, coverage,
positively selected observed entity values without entity IDs, and verified
prediction review status/reason/predicted and observed values without source IDs.
Zero selected remains UNKNOWN about unlisted entities, not physical absence.
Predictions remain separate from observed values; action_success is null.

Fixed source order: real empty, MATCH, MISMATCH, UNKNOWN, synthetic empty; each
prior then following. Within each epoch warmup RAW/SEM, scored RAW/SEM, SEM/RAW,
RAW/SEM, SEM/RAW. Exactly 100 BOUNDED requests, optional THINK up to 200 provider
calls, OPEN zero. Existing instruction, choices, focus, think_allowed, model and
rubric remain unchanged. Freeze all requests before model startup. Immediately
before execution reconstruct the complete plan from original sources and reject
any manifest, payload, order or budget substitution. Retain first terminal and
partial fsynced journal on failure, without retries.

Use the RSEE shared Python3.12, existing Product/S owned_model lifetime,
LlamaCppRelayProvider and RelayEngine. No new launcher or model owner. Pin clean
pushed HEAD before startup, verify existing GGUF/runtime/template, ctx8192,
slots1, temperature0, reasoning_effort=none and cache_prompt=false. Check 82
protected files, 770 historical entries and original A/B/factorial/neutral
hashes before/after. Observe owned PID/starttime/reap/port from a separate
process and read results back independently from frozen files and journal.

Report warmup separately, every source epoch/arm rubric agreement, pair flips,
empty false INSPECT, positive INSPECT, unresolved/THINK/API errors and tokens/
latency. Identity, vocabulary and length covary: no individual-field causal
claim. Repeats from one saved World and fixtures are not independent World tests.
Product adoption requires a separate owner gate, even with favorable DEV results.
CI/FULL/new World/Action/OUTCOME/S10/Memory/SCIENCE zero; PR634 unchanged.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN
