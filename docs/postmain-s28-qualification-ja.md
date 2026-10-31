# RelaySelf S28 — Explicit Mineflayer probe roundtrip qualification

## Frozen authority
- S27 Draft PR #363 exact HEAD `f40c690cf7df005be4a69fe1cd57bb0d29c1070a`.
- Work only in S28 stacked branch. No changes to S18–S27 frozen artifacts, RelayTheory R6, or Paper2 MAIN40.

## Narrow scientific question
S27 projected caller-provided typed Mineflayer observation data into S24 cognitive evidence.
S28 tests one **explicit caller-initiated** `send_observe()` / `receive()` roundtrip in the existing adapter interface, with an owner-local one-shot cursor and bounded sequence verification before invoking frozen S27.

```text
caller proposal to observe != Action authorization
send_observe() != proof of fresh causal response
typed protocol frame != physically authenticated Minecraft World
sequence freshness != wire request/response correlation
observed entity != permission to autonomously rerun cognition or issue Action
```

## Scope and mechanism
`src/relay_self/explicit_probe.py` adds:
- `ExplicitProbeAuthority`: explicit caller grant for exact existing Action3 session and target zombie entity id.
- `ExclusiveProbeCursor`: owner-local one-shot token initialized from terminal S15 WorldConsequence3 after-probe seq4 as next_seq5.
- `request_explicit_post_action_probe`: strict preflight for Action3 terminal supervisor identity, EXECUTED WorldConsequence, exact Mineflayer adapter_started session, seq cursor, time bounds and scope. Then irreversibly consumes the one-shot cursor **before** sending exactly one observe command.
- A bounded `asyncio.wait_for` over one `send_observe` and at most 4 default typed received frames. Session and seq must be contiguous, from the expected next_seq. Non-probe observation kinds may interleave; any unexpected non-observation, wrong session, replay, gap, timeout or exhausted frame budget refuses. No automatic retry.
- On the first qualified probe, invokes unchanged S27 `project_source_native_threat`. Output is existing S24 `PostFailureWorldEvidence` inside a structured S28 roundtrip receipt. It creates no Action authority or next epoch.

## Positive / negative evidence
Two independent deterministic Mineflayer adapter sessions:
- after Action3 WorldConsequence3 after-probe seq4 → `send_observe` once → new `probe` seq5. Exact zombie #42 at 0.2m projects 20cm → explicitly invoked existing S24 selects MOVE_AWAY; 1.8m projects 180cm → S24 selects WAIT.
- interleaved `entities` seq5 followed by `probe` seq6 allowed only with exact contiguous sequence, within max_frames.
- repeated same cursor cannot cause second send; bad caller authority, wrong Action3/session/parent/cursor rejected before sending.
- wrong session, replay, missing seq, untyped response, absent target, non-probe exhaustion, send error, timeout refuse projection; cursor is consumed after a send attempt.

S24 cognition, Current Intent, retained 4/rev1 and Action1–3 terminal outcomes remain unchanged except explicit EpochPlan entry. There is no Action issue.

## Critical limitation: request ID and authenticity
The frozen Mineflayer adapter `observe` command has **no request ID**, and observations do not echo request IDs. S28 therefore qualifies only a **serialized, caller-exclusive, strictly ordered typed roundtrip** in deterministic adapter tests. A queued unsolicited probe matching the expected sequence can be indistinguishable from the requested response. We deliberately do **not** classify exact request/response causality, physical provenance, independent freshness of the wall clock, bridge attestation, global exactly-once or live Minecraft execution as proven.

The exclusive cursor is local and mutable only for replay rejection within the same process and caller-held token; it is not persistent/global state. The inspected/observed timestamp is supplied by the caller; no cryptographic source timestamp exists in frozen protocol. No automatic listener/scheduler, autonomous reentry, new skill/action, new learning, generalized threat inference, or global memory owner.

## Acceptance gate
`SERIALIZED_EXPLICIT_MINEFLAYER_PROBE_ROUNDTRIP_QUALIFIED` is accepted only after exact final HEAD four-job CI (repository contracts, pytest, Ruff, Mineflayer adapter) succeeds. PR remains Draft/unmerged.

S29 candidate: introduce a separate correlated observe request ID in both Node bridge command and Python protocol response, preserving backwards compatibility or frozen semantics, then test causal request/response correlation. Any live Minecraft server experiment requires separate explicit setup.
