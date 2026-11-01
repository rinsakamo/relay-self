# L Lane — MP11 live prior S49 action prefix source (DEV opt-in)

2026-11-01. Stacked on L Draft #671 (itself on #668 / G3 #666). Issues #431 / #653. `main`, M, WB and G4 remain unchanged.

## New development boundary

The G3 physical World demonstrated original S49/S16 actions and 8-tick original Paper windows three times, but the existing L/MP12 cognitive analysis was **postrun retrospective**. This increment adds an explicit, default-OFF, original S49-owned **online sample point**, just after the original native Action/S16 closure and after complete Paper WAIT8 + INPUT8 + seven original forecast pairs, **before the next original S49 action callback**.

The existing S49 process only, under command flag `--l-mp11-live-prefix-dev` and environment `L_MP11_LIVE_PREFIX_DEV=1` and existing G3 original grants, samples the currently growing server log, truncates to the last complete newline, checks the original native typed S16 Action/sequence, source-bound marker and original same-World paper-source lock. A strictly bounded read-only `LivePriorLedger` checks each new prefix as an append-only extension of the preceding byte prefix (no changed old bytes), exactly one new original marker with PRE/POST, WAIT BEGIN, 8 consecutive WAIT/INPUT and 7 frozen/score pairs, no future foreign marker, exact World/subject/session, monotonically increasing native S16 seq, and finite source coordinates. It never calls an LLM. The next L2 request only contains completed previous Action observations, source limits and hashes.

Default G3 mode remains unchanged; S49 / S16 / S15 / Paper control and all action issuance stay with original owner. The new witness flags are **unsealed original Paper source sampled while alive** and **S49 typed S16 claim**, not independent postrun W3/Paper qualification. Each snapshot SHA is a prefix digest, not an attested final original SHA; Paper input is only a last-reported callback witness and physical effective clear tick remains unknown.

## Strict scope

- New World 0, physical S49 Actions 0, real Gemma calls 0 in this PR. No live physical claim until a separate on-device run captures actual new prefixes and the final independent original readback reconciles all earlier prefix SHAs.
- Hypothesis tests and model revisions are not wired here. L2 receives an OPEN **request schema only**, not a generated model answer. The original three G3 trials are same GRASS and same MOVE_BACKWARD and did not vary physical input regime.
- Existing G3 next Action remains original autonomous L0 hazard response, NOT a response to L2's suggestion. The flag cannot change choice, timing, World mutation, fatigue, L1 Habit or L0 reflex. An incorrect source fails closed in explicit DEV mode.
- Offline tests use SYNTHETIC Paper-line segments. Green CI does not certify live server ticks, early callback timing, original stdout, or the physical experiment.
- Prior MP12 #667 includes independent real historical original-source qualification and local llama.cpp replay; this change is complementary because its source snapshot is taken online rather than reconstructed after World shutdown.

## Next real milestones

1. Execute one fresh DEV Paper World with L prefix flag, existing G3 original mode and original native source capture, and independently reconcile each original in-run prefix against final original Paper/W3 sealed bytes.
2. Only then connect an actual bounded Gemma `RelayEngine.open` after previous completed evidence, without model authority to issue any S49 action.
3. Introduce explicit different SHORT/LONG and/or grass/ice actual physical conditions through the existing authorized S49/Paper owner and safety budget, and freeze predictions before each affected Action.
4. Evaluate independent heldout unseen conditions and cheap baselines over epochs; only source-/goal-qualified experiences could later become L1/Habit candidates. No automatic L0 promotion.

`L_MP11_LIVE_PREFIX_PREPARED_OFFLINE_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
