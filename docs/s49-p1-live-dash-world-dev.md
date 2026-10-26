# RelaySelf S49 → Paper → P1 fatigue-gated physical DASH (DEV)

Date: 2026-10-26. All operations were on the isolated
`self/dev-s49-forward-motor-admission-20261026` branch.

## Measured outcome

Exact real-World source HEAD: `126e0e31e6d951181c1bfd11b01e2eb60109b28d`.

- [P1 live physical DASH run 40307487657 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40307487657)
- [Original P1-OFF DASH regression run 40307487649 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40307487649)

One disposable Paper 1.21.8 World, original S49 single issuer,
`MOVE_FORWARD_SPRINT_DEV`, original Action and S16 cleanup/outcome 2/2,
Java/Node exit 0. 13 Paper full-time ticks were logged and independently
replayed by Python `experiments.p1_gait_dev.advance_gait_dev` against the
**same single fatigue dimension** (no sprint-stamina gauge).

| Measurement | P1-live | P1-off regression |
| --- | ---: | ---: |
| P1 initial fatigue | 0.6000 | Disabled |
| P1 final fatigue | 0.6155207399 | Disabled |
| DASH first applied power | 0.8021972523 | 1.0 |
| DASH final applied power | 0.7722848698 | 1.0 |
| Paper native callback World ticks | 13 | 13 |
| Paper boost ticks | 10 | 11 |
| Paper sampled XZ peak, nominal 20 TPS | 7.727658148 m/s | 8.402464276 m/s |
| Native first P1-armed action displacement | 3.814361291 m | 4.124919782 m |
| Native second unarmed action displacement | 3.030157210 m | 3.030157205 m |
| Native armed minus unarmed displacement | +0.784204082 m | +1.094762577 m |
| Original S49 native OUTCOME | 2/2 | 2/2 |

**This was NOT a matched scientific A/B comparison.** The
separate P1-off regression is only a useful engineering reference.

The new `p1_motor_power_limit_dev` uses the existing P1 state and
permitted extra M0 budget: at fatigue F/capacity <=0.5 it admits the
requested power, and at F/capacity 0.5..1 it monotonically limits
power via `2*(1-F/capacity)`. The existing analytic P1 net
load/recovery and its nominal full-power 20-second design anchor
remain intact. This is an additional **DEV motor limiter** and does
not independently qualify fatigue physiology or a 20-second full-World
trial.

## How the World observation is connected

The temporary Paper plugin is started ONLY by the original S49 issued
forward+sprint Action wrapper and releases its speed modifier at the
original Action cleanup. With explicit `p1-live-dev: true`, the Paper
callback advances one P1 fatigue value per elapsed Paper World tick,
using the **previously applied physical boost** (or RUN when no boost),
and sets the same transient movement speed attribute modifier
according to the current P1-limited DASH power.

The disposable runner persists unedited `S49_DASH_DEV_TICK` lines
including `p1_before`, `p1_after`, `p1_prev_applied_power`, and
`p1_current_applied_power`. A separate Python reviewer replays all 13
observed consecutive tick transitions through
`advance_gait_dev` and compares both fatigue and power against
`p1_motor_power_limit_dev`. Missing ticks, foreign session, wrong
fatigue, inflated output, and non-finite evidence fail closed. P1-off
behavior and old S49 movement commands remain unchanged.

## M0 and evidence boundary

DEV local estimate: extra M0 charge **0.0786981057** over the replayed
Paper ticks. This is **not a ledger debit**. There was no authorized
M0 posting, initial M0 energy was not modified, and unobserved
terminal ticks were not billed retroactively. No M0 credit was minted.

Paper input forward packet flags were still empty. 10 Paper boost
ticks were labelled `MOTION_PROJECTION`, not authenticated input
edges. World/Paper/client clock alignment, hard directional speed
caps, live multi-Action P1 continuity, M0 authority, and R/SCI
qualification were **not** demonstrated.

Classification: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
Preserve main, PR #545 and Draft PR #634. The next engineering step
is source-qualified Paper↔S49 World tick custody plus a pre-existing M0
owner's explicit debit authority, using isolated DEV evidence first.
