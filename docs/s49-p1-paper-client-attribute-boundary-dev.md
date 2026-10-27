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

## Verified original S49 real-World OFF/ON result — 2026-10-27

**Exact code tested HEAD** `3d60df95041689d4aabd3b54d88b13505f24e1a8`.
GitHub Actions [#40487527583](https://github.com/rinsakamo/relay-self/actions/runs/40487527583) **SUCCESS**: Python 3.12 focused **161 PASS**, Ruff **PASS**; Node 22 speed-projection **3 PASS**; Java 21 Paper plugin `BUILD SUCCESS`; two genuine disposable Paper 1.21.8 Worlds, original S49 two S16 Action OUTCOMEs in each, Java/Node exits 0.

| Genuine observation | client attribute sync OFF | client attribute sync ON |
| --- | ---: | ---: |
| Fresh S49 session | `21f11933-9245-429f-b665-0208d1189362` | `9258511c-3df5-4940-8f1a-2735ccc7bbe4` |
| Same historical hypothetical P1 initial F | 0.6177122410202606 | 0.6177122410202606 |
| Paper first applied DASH power | 0.7668612208455023 | 0.7668612208455023 |
| Paper boosted tick samples | 11 | 11 |
| Local Node raw Paper DASH packet observations | **6** | **5** |
| Node decoded `generic.scale` with DASH observed | **22** | **19** |
| Node `minecraft:movement_speed` with DASH during actual physicsTick | **0** | **9** |
| Node `minecraft:movement_speed` with DASH overall trace | **0** | **19** |
| Node active phase displacement (local frame subset), m | 2.902757114402002 | 3.7277651669850753 |
| Paper sampled peak horizontal speed, m/s | **5.608397378309604** | **7.684371248139037** |
| Original first Action native S16 XZ distance, m | **3.0301571644943603** | **3.855165217077433** |
| Original second unboosted S16 XZ distance, m | 3.0301571644943603 | 3.0301572054686403 |
| Paper P1 fatigue at end of first DASH (model only) | 0.6339858478899532 | 0.6339858478899532 |
| M0 original S49 DEV remaining | 10.417412841409345 | 10.417412841409345 |

Observed physical first Action delta **+0.8250080525830725 m** and sampled Paper peak speed **+2.0759738698294328 m/s**. In its *own* World, the sync-enabled first Action also exceeded the existing native-vs-unboosted gate (gain 0.8250080116087926 m and peak 7.684371248 m/s). OFF did not.

### Engineering conclusion

The incoming Paper DASH bonus was already in the received client packet (`generic.scale`). It was **not** visible to the Mineflayer physics engine as a `minecraft:movement_speed` bonus with sync OFF. With the existing guarded DEV attribute mapper enabled, the bonus appeared in **9 actual Node physicsTick observations** and physical movement increased alongside it, despite identical P1 input, first-Paper power and scripted native preconditions. This strongly supports missing client attribute propagation as the cause of the prior pair's null movement effect, rather than the P1 single-fatigue formula.

**Limits:** Two different disposable Worlds are not a randomized or world-tick-phase-matched physical experiment. Visibility of a key alone is not complete proof that it was consumed in every physics integration step. This verifies **DEV motor output**, not true same-Self WAIT recovery, an independent P1 sensor, physical DASH terminal cap, R WorldTick, or L0 control policy qualification.

New read-only Node-local file `node_speed_attr_boundary_dev.json` is source-reviewed and exclusive-created for the original first Action, bounded to its SET/CLEAR; no new Mineflayer packet stream, receiver or issuer. Existing S49 S15/S16 and original M0 DEV posting remained sole owners. No MAIN/PR merge.

Artifact **12726455010** `p1-attribute-boundary-pair-40487527583-1`,
digest `sha256:62f16343cfce268f03dc182c2d159bcfd2517a8c7f47e9092e8351a53f36bfa8`.

Pre-World failure runs **#40487281917** (Ruff F841 unused variable) and **#40487396668** (fixture reader erroneously rejects Linux `PosixPath`) were repaired on the isolated branch. Neither failed run launched a World. The successful World run is a fresh run #40487527583, not a reinterpretation of failed runs.

**Next DEV experiment:** enable the already-tested attribute projection in both fresh Worlds using the two historical P1 model F values (CARRY versus WAIT_ASSUMED), then compare actual native movement and Paper speeds. This would demonstrate whether modeled fatigue affects *motor response* once the projection boundary works, but still would not establish real WAIT recovery or R admission.
