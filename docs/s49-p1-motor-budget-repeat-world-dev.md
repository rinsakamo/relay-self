# RelaySelf — S49/P1 MotorBudget two-pair repeat DEV

**Date:** 2026-10-25. **Classification:**
`DEV_REPEAT_TWO_INDEPENDENT_WORLD_PAIRS_RECORDED`,
`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Objective

Repeat the preceding two separate Paper 1.21.8 World conditions **once**
and exercise a minimal explicit interface between the P1 *hypothetical*
body capability and the original issued S49 native motor command.
Treat neither hypothesis nor elapsed control time as direct observed
bodily fatigue or source-attested World ticks.

- Prior frozen first pair: run
  [40181302973](https://github.com/rinsakamo/relay-self/actions/runs/40181302973),
  artifact [12594212819](https://github.com/rinsakamo/relay-self/actions/runs/40181302973/artifacts/12594212819),
  exact World HEAD `dce06b9a2f52ce94c4f63f5352e30c1280023a13`.
- Repeat pair: run
  [40183517844](https://github.com/rinsakamo/relay-self/actions/runs/40183517844),
  artifact [12595222668](https://github.com/rinsakamo/relay-self/actions/runs/40183517844/artifacts/12595222668),
  exact World HEAD `f690d24035371c3bfeb1789f9be95ae9fcd0ad39`.
- Repeat runner isolated branch `self/dev-p1-motor-repeat-20261025`.
  Protected source blob SHA unchanged:
  `normal_action.py = 0ded8fa296c92076a643de08cd6fc360061e1d08`,
  `fatigue_p1.py = bd4f35a4079da0770ef11cdec921dbba31de9b81`.
  The predecessor DEV-only original S49 runner opt-ins are not yet
  adopted into the Draft PRs or main.

## Minimal DEV actuator interface

New `adapters/mineflayer/s49_p1_motor_budget_dev.py` defines immutable
`DevMotorBudget` and `propose_issued_motor_budget_dev()`.
`DevMotorBudget.apply_to_issued()` takes an existing authorized
`MineflayerCommand` and pure-replaces **duration_s only**.
Rejects mismatched issued Action identity, modified nominal command,
source/probe mismatch, synthetic source-bound ticks, native-fatigue
claims, inserted WAIT, additional Action issuers/readers or Action grant,
or R/science admission.

The original S49 S14/S16 authorizer, sole Mineflayer native receiver,
L0 decision policy, executor and cleanup remain the command owner. The
DEV outer runner invokes the proposal solely after original issuance,
not as a new Action, and records the original nominal duration from
`proposal.nominal_duration_s` *before* replacing the command.

`tests/test_s49_p1_motor_budget_dev.py` includes both model-rate
positive cases, immutable S15 command identity/readback, and explicit
fail-closed forged authority, sensor, tick, profile, duration and action
identity negatives. Python **3.12** focused, syntax/Ruff, Java21 observer
build, Node22 npm ci, pinned Paper asset verification, real two World
runs, strict native S16 source review and repeatability review all PASS.

## Results: two independent pairs / four fresh Worlds

Six original S49 L0 decisions and **four actual native MOVE S16
terminal OUTCOMEs per World**, Java and Node exit0/0, original sole
session owner, matching sixth native pre-MOVE zombie 2.0 blocks,
health/food 20/20 and y=-60. Third MOVE geometric distance
0.6269065734 blocks in both repeat Worlds; the P1 model is derived
from this native result.

| Real original sixth issued Action | First pair | Repeat pair |
| --- | ---: | ---: |
| Original P1 0.1964893232 s | 0.6269065734 block | **0.4302315372 block** |
| DEV uncalibrated stress 0.0600000000 s | 0.0980000385 block | **0.0980000385 block** |
| Stress minus Original P1 displacement | -0.5289065349 block | **-0.3322314986 block** |

**Observed direction repeated in 2/2 scripted pairs.**
However the original-rate arm varied **0.1966750363 blocks** across
runs despite nominal control duration and near-zombie geometry
matching. The 0.060-second high-stress arm happened to yield
practically equal 0.098-block distances in both runs. This is
consistent with event-loop/tick cadence impacting the precise response;
the two distinct World clocks and Action histories were not matched or
attested tick-by-tick. Two pairs do not establish robust repeatability,
a calibrated physical sensor, linear command-time physics or a causal
physiological fatigue mechanism.

The P1 stress rate is `6.0` versus the existing profile `0.04`,
specifically an *uncalibrated sensitivity scenario*; its saturated
modeled fatigue of `1.0` is not measured bodily fatigue.
The verified claim is narrower: a model-only duration proposal passed
the existing Action issue flow, and two matched-script pairs showed
shorter **physical displacement** with the shorter command duration.
No R-admitted WorldTick, WAIT recovery tick, S10 update, SCIENCE or
external actor qualification was performed.

### Immutable failed attempt

First repeat attempt
[40183160003](https://github.com/rinsakamo/relay-self/actions/runs/40183160003)
preserved artifact
[12594852942](https://github.com/rinsakamo/relay-self/actions/runs/40183160003/artifacts/12594852942).
That original S49 run itself **PASSed** six decisions, four Actions,
Java/Node exit0; the outer DEV report **BLOCKED** because the new
adapter erroneously labeled its replaced duration as
`unmodified_original_action_duration_s`.
The actual Action was not reported as a successful paired World.
Fix at `253e4b1b8a5401dfc057d156dc2c9ef652b56ac0` takes
`proposal.nominal_duration_s` for this field; separate successful
repeat #40183517844 was run. The failed run was not retroactively
rewritten/adopted.

## Next

Keep original executor and P1 production physics untouched. A DEV
test on command duration versus observed distance with more
tick-phase variants can inform whether a coarse bounded movement
budget is more robust than a millisecond-rescaled command. Escalation
to formal R/SCIENCE requires separately designed measurement and
source custody; nothing in these two pairs qualifies it.
