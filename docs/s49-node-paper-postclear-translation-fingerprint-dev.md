# RelaySelf — original S49 Node/Paper post-clear translation fingerprint (DEV)

**Date:** 2026-10-26. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
Branch `self/dev-s49-forward-motor-admission-20261026`.
**Exact source-tested HEAD:** `1ec951e5090c09fdda8b406e2749ce3b7d4344c4`.
**[Real disposable Paper 1.21.8 World run #40325860098 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40325860098).**

## New bounded cross-view geometry check

The previous original S49 flow already demonstrated five Node-local
`physicsTick` callbacks after the original `clear_controls` native ACK,
with `forward=false`, `sprint=false` in all five, and five passive
Paper post-release position observations. Both views are **producer-local**
and native Node↔Paper clock synchronization is **not attested**.

This patch adds `audit_node_paper_motion_fingerprint_dev` to the existing
readback. It receives the independently audited original Node and Paper
local reports for the same issued native Action and session. It admits
a **moving translation footprint** only when at least **two adjacent
nonzero** XZ displacements (each >0.01m) match across their individual
ordered sequences within **1e-6m** absolute tolerance. The Paper
mixed-boundary first sample is excluded. No exact Node/Paper tick ID
is compared; unknown offset is an explicit outcome. The matching
algorithm does not permit a single coincidence, zero-to-zero matches,
skipped/missing intermediate samples, nonfinite/negative/teleport
values, foreign session/action, forged controller state, restored DASH
modifier, or invented P1/M0/WAIT authority.

The original S49 executor remains the only Action issuer and
Mineflayer receiver. The new function is offline/read-only after the
original Action and Paper producer-local custody reviews. No new
control path, physical Action, Paper modifier, energy transaction, P1
update, or R/SCI approval is authorized.

The dedicated Node/Paper real World workflow was also corrected to
**actually execute** `tests/test_s49_node_physics_postclear_dev.py`,
`tests/test_s49_node_paper_motion_fingerprint_dev.py`, and earlier
Paper postrelease/ACK negative-control files (previous dedicated
workflow listed some test files in compileall but omitted them from
pytest). Ruff now covers the additional modules and original S15
execution.py. Python 3.12 focused/negative controls, Ruff, Node 22
syntax/bridge tests, Java 21 plugin compile and real Minecraft run all
passed at the source-tested HEAD.

## Actual real Minecraft trace (one disposable World)

| Observation | Source-measured result |
|---|---|
| First original native S49 Action | `s49-native-move-19`, S16 OUTCOME |
| Second original native S49 Action | `s49-native-move-55`, S16 OUTCOME |
| Paper arm/release | tick 244 / tick 258 |
| Original native control applied ACK → Paper delivery marker | seq 23 → tick 246 |
| Original native control clear ACK → Paper delivery marker | seq 35 → tick 258 |
| Paper original DASH motor callbacks | 13 contiguous, 11 speed boosts |
| Node original after-clear physics callbacks | 5; both forward/sprint false 5/5 |
| Node post-clear translation deltas (meters) | 0.2122345417, 0.1158800597, 0.0632705126, **0.0345456999, 0.0188619521** |
| Paper post-release first mixed-boundary delta | 0.1791505724m, excluded from match |
| Paper pure post-release deltas (meters) | **0.0345456999, 0.0188619521**, 0, 0.0159216756 |
| Exact moving fingerprint | **2 adjacent deltas matched within 0.000001m** |
| Node matched ordinal starting index | 4 (of 5) |
| Paper matched pure-postrelease ordinal starting index | 1 (of 4) |
| Node↔Paper exact tick correspondence | NOT ATTESTED |
| Independent third-party source trust | NOT ATTESTED |
| P1 fatigue from 13 original callbacks | 0.600000 → 0.6177122410202606 |
| Original S49 owner M0 energy after 2 MOVE Action steps | 12.0 → 10.413667611509306 |
| DASH extra M0 charge (first only) | 0.08633238849069515 |
| Original Action distances (first vs second) | 3.824499286m vs 3.030157210m |

One World earlier, [run #40323157470](https://github.com/rinsakamo/relay-self/actions/runs/40323157470),
also showed **three consecutive equal nonzero displacements** (about
0.063243, 0.034531, 0.018854 meters) from the two producer-local
streams. The new final implementation actively verifies a matching
two-delta footprint rather than merely asserting such consistency.

## Interpretation and remaining boundaries

The original Node local position changes dynamically across physics
callbacks even after its original `clear_controls` (forward/sprint OFF).
Paper independently samples **changing entity XZ position** after
the original Paper motor modifier was removed. The two sources
share a nontrivial *consecutive geometric footprint* in the same
original session. This reduces the likelihood that the observed
movement is only a stale, repeatedly read single position state.
It does **not** prove the precise event time at which native controls
became physically effective or identify one Node physics tick as one
particular Paper World tick. Producer-local logs are not an R-qualified
external issuer or independent authenticated evidence.

The M0 canonical `basal_cost=0.5` and `move_cost=0.25` remain
**per original M0 logical step**, currently one step per S49 native
MOVE Action. No rate per seconds/World ticks can be deduced from a
sampled motion fingerprint. Post-clear passive readings never
authorize `WAIT`, P1 recovery, M0 basal rate settlement, food,
or additional movement Action.

No FULL/main merge; PR #545 and #634 remain Draft/unmerged. The next
engineering change would need an **explicitly chosen basal
energy-per-second rate** plus an authoritative, gap-checked World
time interval before World-tick M0 posting. Physical WAIT still
requires a distinct source-bound no-control/no-Action interval
beyond the five observed coasting callbacks.
