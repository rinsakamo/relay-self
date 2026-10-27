# S49/P1 speed modifier → Mineflayer client physics boundary — isolated DEV

Status: `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Why

The two genuine Paper 1.21.8 Worlds in run [#40479045528](https://github.com/rinsakamo/relay-self/actions/runs/40479045528) applied different Paper DASH modifiers to two preloaded hypothetical P1 model F values, **but produced identical actual native S16 movement** and sampled Paper speed. Source-bound runtime P1 recovery and physical DASH gain were not established.

The original Mineflayer 4.39.0 bridge already includes a bounded **DEV-only attribute projection**: source packets in the pinned setting expose the player speed in `generic.scale`, while prismarine-physics expects `minecraft:movement_speed`. The projector retains the Paper DASH modifier, but removes duplicate vanilla sprint modifier so that the physics engine handles sprint exactly once. The previous paired workflow did **not** enable `S49_SPEED_ATTR_SYNC_DEV_ONLY`.

## Controlled DEV design

Start two entirely new disposable Paper 1.21.8 Worlds. Both use the **same** counterfactual *CARRY* P1 model F `0.6177122410202606`; change only:

- **OFF**: `S49_SPEED_ATTR_SYNC_DEV_ONLY=0`.
- **ON**: `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`.

Retain the same original S49 3 decisions, 2 native S16 OUTCOMEs, first Paper forward DASH then original unboosted MOVE, original M0 debit ownership and fixed Paper plugin. No independent Action grant, native reader, actual P1 sensor or new motor command.

A **bounded, local** read-only diagnostic on the existing Mineflayer bot, `S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1`, samples: original first S15 SET/CLEAR, client raw `entity_update_attributes` packets, post-project `entityAttributes`, and existing `physicsTick` callbacks with speed attribute map and actual position/velocity. File is exclusive-create, per-World and first Action only. Reporter verifies original session/action identity, monotonic Node-local timestamps, first SET/CLEAR custody and absence of added issuers/readers, independent from Paper clock. No extra native packet stream is created.

A Python 3.12 source reviewer compares: raw Paper modifier packets received, decoded `generic.scale` seen, `minecraft:movement_speed` visible at the physicsTick input, original native first S16 movement, Paper speed, unchanged model initial fatigue and native preconditions. The reviewer **does not** infer that the physics engine necessarily *consumed* the key simply because it was present; that causal edge requires real movement discrimination or tighter measurements.

What this can establish: presence/absence of client-side attributed speed under OFF versus ON and native response under the same hypothetical model. What this **cannot** establish: actual same-Self WAIT recovery, physical fatigue, synchronized server and client World clocks, production-safe maximum DASH capability.

## Verification

- Python 3.12 focused and Ruff, Node 22 bridge syntax and 3 existing speed-projection tests, plus negative controls of forged packets, duplicated ticks, changed actor/profile/preconditions.
- Build the existing isolated Paper motor plugin with Java 21.
- Run 2 fresh genuine disposable Worlds, independently recheck original typed S15/S16 and captured Node trace. Preserve raw records even on failure.
- Original main and Draft PRs stay untouched; no R QUAL, SCIENCE, FULL or production state adoption.

The exact tested code SHA, run, artifacts and outcome must be recorded **after** inspecting the actual jobs.
