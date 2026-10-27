# P1 seven-Paper-bonus-tick stable-phase comparison — DEV

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Existing original-S49 real evidence

[2026-10-27 run #40495397519](https://github.com/rinsakamo/relay-self/actions/runs/40495397519) confirmed two genuine disposable Paper 1.21.8 Worlds with exactly **seven consecutive positive Paper boost callback ticks each** (and six Node-active projected speed-attribute physics ticks in each). First original S16 native XZ distance was CARRY=3.647398724622718m and WAIT_ASSUMED=4.12577858180323m: difference +0.4783798571805118m, but exact server/client phases remain unjoined.

Paper's positive-ordinal 1 sampled speed had a large phase-sensitive difference (CARRY 3.9392m/s vs WAIT_ASSUMED 8.6380m/s), even though Paper samples speed from **movement preceding that callback's modifier update**. Omitting that first sample, the original ordinals 2..7 had a reported mean +0.581982219263m/s difference. Physical P1 recovery is not inferred.

## New read-only measurement

This isolated downstream DEV stage uses the **same original S49 two-Action owner and unchanged seven-positive-Paper-tick cap**, launching two new disposable Worlds at the exact two prior *hypothetical* P1 F preloads. No native motor or P1/M0 producer code is changed.

The new `adapters/mineflayer/s49_p1_steady_phase_review_dev.py` independently reruns the existing original S49 source evidence, complete Paper P1 replay, Node client speed attribute trace and seven-tick owner-capped source auditors. It compares:

1. Paper *bonus-ordinal* 2 through 7 speeds and applied model powers, excluding the phase-sensitive first positive row. The six values are compared positionally within each World, **not as synchronized absolute ticks**.
2. Already-produced Node `ACTIVE_PHYSICS` source-local rows, using only consecutive callbacks where the Paper DASH modifier is visible in the actual `minecraft:movement_speed` physics attribute. For each consecutive pair, compute horizontal distance from the original Node XZ position and a descriptive 20Hz nominal speed proxy. The first positive callback has no prior same-state interval, so it is excluded. Report the shorter common prefix if callback counts differ; never fabricate intervening samples.
3. The existing original S49 S16 displacement as a separate whole-Action measurement. The Native Action duration remains **unmatched**, and Paper versus Node local clocks remain **unsynchronized**.

Input checks reject foreign session/action, bad Node source shape, missing continuous active physics, impossible position jumps, invalid modifier operation, changed official qualification flags, source switches and invented extra Action issuers/readers. The self-identifying raw Node source SHA256 is recorded; the prior Paper reviewer already binds SHA and World identities.

Outcomes may be positive, zero or negative in native/Node speed; none grants L0 power. No runtime production P1, actual longitudinal WAIT recovery, new native reader, M0 posting, R-qualified WAIT, SCIENCE, FULL, main or Draft PR update.

## Verification

- Python 3.12 focused tests (new negative controls plus existing matched boost and native source), Ruff before World.
- Node 22 original bridge syntax plus existing speed attribute regression tests, Java 21 Paper plugin build.
- Pinned genuine Paper 1.21.8 build 60, two disposable original S49 sessions, first 7 speed-modifier ticks only.
- Upload *all original trial files*, including failures, before treating a cross-World speed delta as source-verified.
- GitHub workflow: `.github/workflows/self-p1-steady-phase-motor-dev.yml`.

Exact tested SHA, run ID and resulting real measurements to be appended only after successful readback. This does **not** yet replace an owner-tick-matched native first Action.
