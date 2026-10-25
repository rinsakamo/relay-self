# RelaySelf — repeated real Minecraft P1 gait pair + typed DEV motor boundary

Date: 2026-10-25
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Engineering scope

Isolated branch: `self/dev-p1-pair-repeat-motor-interface-20261025`.
Historical original `adapters/mineflayer/normal_action.py`
blob `0ded8fa296c92076a643de08cd6fc360061e1d08`, original
`experiments/fatigue_p1.py` blob
`bd4f35a4079da0770ef11cdec921dbba31de9b81` unchanged.

This DEV candidate adds `s49_p1_motor_envelope_dev.py`:
`DevMotorEnvelope` is an immutable typed candidate containing original
session, native fifth/sixth probe sequence, original already-issued
Action ID, third-Action source ID, P1 model profile, and bounded
command duration. The pure function `apply_issued_p1_motor_envelope_dev`
only returns a copy of the existing `MineflayerCommand` with a
different `duration_s` **after the original S49 executor has
independently issued the Action**. It refuses stale/foreign native
probes, changed issue identity, unsupported original command, invalid
model input, out-of-range durations, extra issuers/receivers, or
fabricated R/Science qualification. The sole owner keeps one-shot
control and S14/S15/S16 permissions; the original production executor
and P1 model are not changed.

New `tests/test_s49_p1_motor_envelope_dev.py` covers baseline/stress
positive outcomes and 17 source/authority/duration negative cases.
Python3.12 focused tests, syntax and Ruff:
[Actions #40182421100](https://github.com/rinsakamo/relay-self/actions/runs/40182421100) **SUCCESS**
at exact HEAD `59ead0abaf8dafde304e1dfc7d9c0d4b5afbbef3`.

## Repeated paired fresh Minecraft World measurements

Two prior DEV arms, one original-rate P1 model and one intentionally
uncalibrated `move_per_block=6` sensitivity, were **repeated once**.
All four separate Worlds across the two independent pairs started
fresh and completed the same original S49 six-decision/four-Action
trajectory (WAIT, MOVE, MOVE, MOVE, WAIT, MOVE).
Observed sixth native preconditions in each pair: nearby target 2
blocks; health20, food20, y=-60; the third MOVE distance
approximately 0.6269 blocks. S16 original receipts all OUTCOME,
Java/Node exit 0/0 in both repeated Worlds.

| Paired scripted World evidence | Pair 1 | Pair 2 |
| --- | ---: | ---: |
| GitHub Actions | [#40181302973](https://github.com/rinsakamo/relay-self/actions/runs/40181302973) | [#40182155813](https://github.com/rinsakamo/relay-self/actions/runs/40182155813) |
| Baseline model command | 0.1964893232 s | 0.1964893232 s |
| Baseline native sixth MOVE | 0.6269065734 block | 0.6269065734 block |
| Uncalibrated strong-stress command | 0.0600000000 s | 0.0600000000 s |
| Stress native sixth MOVE | 0.0980000385 block | 0.2495080981 block |
| Observed distance difference (stress minus base) | -0.5289065349 block | -0.3773984753 block |
| Both inner/outer World runs | PASS | PASS |

Pair 2: new [run #40182155813](https://github.com/rinsakamo/relay-self/actions/runs/40182155813)
exact HEAD `cc08979b0db9596ec7366167b0e72ef9c87fff42`, artifact
[#12595185454](https://github.com/rinsakamo/relay-self/actions/runs/40182155813/artifacts/12595185454).
The artifact ZIP was separately read back: two different sessions, both
original report status PASS, Java/Node exit0, 6 decisions, 4 successful
Action OUTCOMEs, original and outer JSON records, and final paired
review `DEV_PAIRED_SCRIPTED_WORLD_MEASUREMENT` PASS.

**Descriptive engineering result:** The direction of response
(shorter DEV command, smaller native displacement) was repeated
in 2 scripted pairs. However, the stress arm displacement varied
0.098–0.250 blocks between the two runs, a spread of
0.151508 blocks, while nominal-rate baseline displacement was
stable to the recorded precision. Asynchronous timing and
Minecraft's discrete World ticks may account for variability.
There are not enough trials to estimate a controlled effect
distribution or infer biological fatigue.

## Live original S49 motor command through NEW typed boundary

Separate fresh single-world smoke execution:
[Actions #40182495497](https://github.com/rinsakamo/relay-self/actions/runs/40182495497)
at exact HEAD `8280217ad85081f2cd0ac41334b71aaa7eec632f`,
[artifact #12594761877](https://github.com/rinsakamo/relay-self/actions/runs/40182495497/artifacts/12594761877).

Original `s49_normal_session_real_ci.qualify()` on a disposable
Paper 1.21.8 / Java21 / Mineflayer Node22 produced six original
L0 decisions and four S14/S16 native MOVE OUTCOMEs.
Original and outer reports **PASS**, Java/Node exit0.
The fourth MOVE `s49-native-move-98` reached original terminal
OUTCOME, moved `0.6269065734210608` blocks and used the typed
DEV boundary to change only duration from `0.20 s` to
`0.19648932318884205 s`; a single native
session, one issuer and no new Action grant were maintained.
The raw ZIP reports and Paper logs were downloaded and checked.

## Boundaries and next engineering priority

This is a **model-conditioned motor timing effect**, not a
demonstration that actual measured fatigue reduces actual physical
movement. The amplified fatigue scenario is deliberately artificial.
The same scripted World preconditions are *not* proof of identical
World-tick histories. `SourceBoundTick(WAIT)` remains absent,
R-admitted ticks 0, no real P1 fatigue sensor, S10 updates 0,
and no V Science experiment.

The isolated branch inherits original
`s49_normal_session_real_ci.py` protected-source DEV amendments,
so merging into PR #545, PR #634 or main requires owner/source review.
No production/default Action/LLM behavior, protected historical
archives, or Draft PR head has been changed.

**Next:** stop creating more World variants until a concise
tick-aware movement boundary has been specified: distinguish physical
World tick, intended input duration, observed displacement and
untested model parameters. Use calibrated data before interpreting
model fatigue as a physical capacity measurement.
