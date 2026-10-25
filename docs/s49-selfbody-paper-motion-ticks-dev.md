# RelaySelf — Paper Input-Edge Negative + Server Motion Tick DEV

Date: 2026-10-25. Isolated branch:
`self/dev-s49-paper-input-edges-20261025`.

**Final DEV result:** `DEV_PAPER_SERVER_POSITION_EVENT_TICKS_OBSERVED /
DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Purpose

Measure server-side movement on the disposable Minecraft Paper 1.21.8
World without conflating:
1. Python/Node local requested milliseconds,
2. Mineflayer client physicsTick callbacks,
3. Paper server-side World.getFullTime ticks,
4. Paper's PlayerInputEvent input-edge signals, which may not be delivered
   for this Mineflayer client, and
5. server-effective action ticks, which remain **not attested**.

Preserve the existing original S49 single issuing/receiving Action owner,
S14/S16 authorization, original `normal_action.py`, `bridge.mjs`,
and P1 fatigue calculator.

## Attempt 1: existing Paper pre-arm input observer (negative)

The original existing Paper `relays49preobserve` was armed **after
original S49 issued its second authorized MOVE and before its original
S15 native dispatch**. The observer logged `S49_OBSERVER_PRE_ARM`
at Paper world tick **441** for the original second Action
`s49-native-move-48`. It never logged `S49_OBSERVER_BACK_TRUE`
or `S49_OBSERVER_BACK_FALSE`.

After 240 World ticks of pre-arm waiting, the observer logged
`S49_DEV_BACK_WAIT_ABORT reason=PRE_ACTION_TIMEOUT_OR_CLOCK_RESET`
without WAIT samples. Outer DEV / original S49 trial **FAIL**, Java and
Node cleaned up with exit 0. The original S49 report retained only
its first terminal native Action; the second execution was not
retroactively asserted to be a complete S16 terminal.

- Run [40188332406](https://github.com/rinsakamo/relay-self/actions/runs/40188332406);
  retained original artifact
  [12597237136](https://github.com/rinsakamo/relay-self/actions/runs/40188332406/artifacts/12597237136).
- Initial run [40188244518](https://github.com/rinsakamo/relay-self/actions/runs/40188244518)
  did not reach Minecraft (preworld import-order Ruff failure).

**Interpretation:** Paper PlayerInputEvent BACK edges cannot be assumed
to be emitted by the original Mineflayer `setControlState()` route.
This is a *failed* server input-edge measurement, **not** measured
zero physical movement or zero server-effectful ticks. It must not
be backfilled with inferred input-edge timestamps.

## Attempt 2: passive Paper position-change event observation (success)

Extended the **existing DEV-only Paper observer** with separately
bounded, console-only `relays49motionstart` /
`relays49motionstop` commands. This listener records at most 64
synchronous `PlayerMoveEvent` X/Z changes on the main Paper thread,
tagged with its `World.getFullTime()` tick and claimed native
Action/session/world. Its one-shot permission is **separate** from
the existing eight-tick post-Action WAIT observer, which remains
operational; no physical action, movement control, or additional
Mineflayer native read loop is added.

A scoped DEV adapter prearms motion sampling after original S49
authorizes the second MOVE but before Node dispatch; it waits for
Paper `S49_MOTION_SERVER_ARM`. The same original motor executor runs,
returns a real S15 consequence, and the scoped adapter issues one
read-only Paper `S49_MOTION_SERVER_COMPLETE` boundary command.
The original S49 S16 closes its Action, and its old post-Action Paper
WAIT observer operates normally. The new report refuses foreign
Action IDs, sessions, reordered ticks/frames, missing starts/stops,
excess samples, nonfinite positions or false input-edge claims.

**Successful single fresh World**:
[Actions run #40188988032](https://github.com/rinsakamo/relay-self/actions/runs/40188988032)
at exact World HEAD
`abd8080adc29ad70088ebaa8bca179b21e9ed6b2`,
original
[artifact #12597038574](https://github.com/rinsakamo/relay-self/actions/runs/40188988032/artifacts/12597038574)
directly downloaded and inspected (5 files, including original S49,
Node timing and complete Paper log).

Original S49 session
`870ffa8a-da12-468d-856e-8ed0255c7267`;
original host **six real L0 decisions and four native S16 closed
MOVE OUTCOMEs**, Java and Node exit0/0.
Python3.12 scoped tests/Ruff, Java21 Paper plugin compilation,
Node22 original bridge package, pinned Paper verification: **PASS**.

| Original S49 Action | Node BACK ON→OFF ms | Client physicsTick callbacks | Original S16 XZ displacement |
|---|---:|---:|---:|
| `s49-native-move-18` | 200.851 | 4 | 0.626907 blocks |
| **`s49-native-move-46`** (Paper sampled) | **201.692** | **4** | **0.626907 blocks** |
| `s49-native-move-67` | 201.111 | 4 | 0.626907 blocks |
| `s49-native-move-94` (SelfBody compensation) | 148.297 | 3 | 0.430232 blocks |

**Paper read-only observations for second Action
`s49-native-move-46`:**

- `S49_MOTION_SERVER_ARM` at server World tick **445**,
  before original Node motor dispatch.
- Five consecutive Paper `PlayerMoveEvent` position-change
  rows, one each at server World ticks **446, 447, 448, 449, 450**.
- Paper position at first event from
  `x=10.5, z=-1.324936176737139`, last event to
  `x=10.5, z=-2.091460863054678`.
- **Total net displacement 0.7665246863 blocks across these
  five Paper events**. This differs from S16
  **0.6269065734** because the Paper sampled movement-event
  interval and S16 before/after observation boundaries are
  **not equivalent**. No lag magnitude is computed by subtraction.
- `S49_MOTION_SERVER_COMPLETE`: five events, five distinct
  server position-change ticks, same claimed session/World/Action.
- Original existing post-second-Action Paper WAIT observer
  successfully sampled consecutive server ticks **463–470**.
- **Paper `PlayerInputEvent` BACK ON/OFF edges remain unobserved.**
  The five server position-change ticks are **not** certified
  effective BACK-control ticks.

## Strongest supported inference

In one DEV World, original Node requested ~201.7ms of BACK,
Mineflayer performed 4 client `physicsTick` callbacks while BACK
was active, Paper independently reported player position changes
on 5 consecutive World-full-time ticks, and the original S16
measured ~0.627-block X/Z net change.

This is an actual cross-system **observation of distinct time
domains**, not a synchronized causal mapping. Input latency
per transport hop, server-on/off effective tick count and model
calibration remain unknown. Paper position observations are
read-only but their addition may perturb execution; no claim of
unbiased latency estimation, R source authentication or
physiological fatigue.

The sampled original S49 was not modified. Source SHA:
`bridge.mjs` `42b5a8f1ff49a1728727844fbb4533a95bb34bcf`;
`normal_action.py` `0ded8fa296c92076a643de08cd6fc360061e1d08`;
`fatigue_p1.py` `bd4f35a4079da0770ef11cdec921dbba31de9b81`.

## CI and classification

The successful physical run followed a PREWORLD
[Ruff E702 check failure #40188876004](https://github.com/rinsakamo/relay-self/actions/runs/40188876004)
(DEV test fixture single-line semicolon), corrected without new
World. The failed pre-arm run and prior import Ruff failure are
retained separately; none reclassified as PASS.

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
No full regression, new receiver, L0 motor Action permission, S10
update, fatigue sensor, World-tick qualification, main merge or Draft
PR #545/#634 changes.

### Next sensible engineering task

If accurate SelfBody movement control is the priority, prefer
**closed S16 movement outcome → bounded next-command correction**
with variance/uncertainty estimates. Paper position-event ticks
can be an optional independent DEV diagnostic; do not redesign
the Action execution loop around the missing PlayerInputEvent
or equate server motion-event ticks to source-certified actuator
timing.
