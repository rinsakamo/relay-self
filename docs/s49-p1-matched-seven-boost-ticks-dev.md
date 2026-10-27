# P1 hypothetical motor response at seven matched Paper bonus ticks — DEV

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Question

Earlier [DEV real World #40491478791](https://github.com/rinsakamo/relay-self/actions/runs/40491478791) confirmed **motor output sensitivity** to two synthetic P1 model initial F states, with the existing Mineflayer speed-attribute bridge enabled in both Worlds:

- CARRY F=0.6177122410202606, first S16=3.759799 m; 10 positive Paper bonus callbacks
- WAIT_ASSUMED F=0.21616083122103735, first S16=4.264898 m; 11 positive Paper bonus callbacks

A +0.5051m native S16 difference was observed, **but** 10-versus-11 boosted World ticks and different Node active attribute physics tick counts confound precise motor difference attribution. No actual same-Self recovery was measured.

## Controlled change, without a second Action owner

The existing **one-shot original Paper DEV speed modifier** gains an optional `p1-matched-boost-cap-dev: 7` when and only when the existing exact two hardcoded synthetic model-F preload scenarios are enabled. The plugin counts **positive modifier-applied World callback ticks**, leaves the original S49 first native Action duration/issuer unchanged, and clears its temporary modifier after the 7th positive tick. This is a motor-only DEV test cap, not an extra timeout, WAIT command, new native reader, new action issuer, or change to P1/M0 authority.

In separate disposable Worlds, the original S49 issues exactly the same first boosted and second unboosted native S15/S16 MOVE actions. Both Worlds use the exact pinned Paper 1.21.8 build, Java 21 plugin, Mineflayer 4.39.0, `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`, `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=1`, and `S49_P1_MATCHED_BOOST_DEV_ONLY=1`. The single intentionally changed motor-model input is the prior frozen hypothetical F:

| Arm | Preloaded DEV P1 model F |
|---|---:|
| CARRY | 0.6177122410202606 |
| WAIT_ASSUMED | 0.21616083122103735 |

Each completed original Action must produce *exactly 7 consecutive Paper World tick rows* with `modifier_applied=true`, `p1_matched_boost_cap_reached=true`, the same player/world/action/session throughout, **at least one subsequent no-boost gait tick**, and a genuine `OWNER_RELEASE` completion. Unexpected extra, missing or replayed ticks, wrong actor, forged P1/M0 authority or wrong cap fail closed.

Source review reuses the original S49 S15/S16 receipt verification, complete Paper P1 model replay and Node speed attribute source trace review. The new pure reviewer then compares **same positive-boost ordinal 1..7** speed and power values and actual S16 displacement for both Worlds. The result may be positive or negative; physical displacement gain is not a condition for valid source evidence.

## Important epistemic boundary

- **7 positive Paper ticks are duration-matched for the *server modifier*, not for the native S49 Action**. The original Action can still run for a slightly different number of Paper/Node ticks.
- Matching by 1..7 ordinal is **not** synchronization of World ticks between two independent Worlds, nor synchronization of Node physics callbacks and Paper modifier timing.
- Server tick speed uses prior-position deltas; the first positive row need not measure the already-applied modifier's physical effect.
- Model F is a deliberately loaded *hypothesis*, **not** a physiological reading or a witnessed same-Self WAIT recovery. No actual P1 state posting, qualified R WAIT, or production L0 DASH power admission.
- Existing M0 posting remains the original DEV S49 S16 owner; new reviewer posts no P1 or M0 entries.
- No R/SCIENCE/FULL runs; main, Draft PR #545 and #634 remain untouched.

### Reproducibility

Run `.github/workflows/self-p1-matched-boost-7ticks-dev.yml` on the isolated opt-in DEV branch. Python 3.12 focused tests/Ruff + Node 22 tests + Java 21 plugin compilation precede both real disposable Paper Worlds. Save raw source traces even on failed validation. Record the *exact* tested HEAD, real run id, artifacts, and measured both-arm comparison only after readback.

Model-hypothesis source SHA256 from the original earlier static candidate: `f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4`.
