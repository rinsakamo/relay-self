# RelaySelf — S49 motor-side DASH direction cap DEV (2026-10-26)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Design decision

DASH stance persists through a sideways or backward input, but the
resulting motor mode is subject to a lower directional speed ceiling.
No artificial DASH cooldown or additional P1 gauge. Keep one P1 fatigue
state and a distinct M0 energy ledger. Do not change original S49 action
ownership, read authority, or archived physical evidence.

Paper Attribute.MOVEMENT_SPEED alone did not establish effective velocity
control for the current Mineflayer motor: applying a -25% server modifier
for five observed Paper callbacks produced the same S49 BACK displacement
as the unmodified control, 0.626906573m. A diagnostic 0.5s host pause
with fifteen observed Paper callbacks also produced no difference.
These are source comparisons, not proof of *why* the control path failed.
See workflow https://github.com/rinsakamo/relay-self/actions/runs/40267056174 .

## Client motor intervention (DEV proof)

The original S49 issuer authorizes two MOVE_BACKWARD Actions. The
DEV-only generated sibling Mineflayer bridge applies the standard
BACK input on both; **on the second BACK only**, it also applies
native SNEAK control *inside the same command effect*. The original
S49 clear-control effect stops all movement. This is a more conservative
physical control, not a new Action grant, issuer, process, JSONL channel
or receiver. No changes to the original bridge.mjs, protocol.mjs,
normal_action.py, or fatigue_p1.py.

Java21 Paper plugin still retains the one-shot DASH stance and records
the backward attribute adjustment; that adjustment by itself is not
claimed to cause the changed displacement. Generated Node bridge receipt
records the second Action ID and the added SNEAK gait control, but a
receipt file is not an independent trusted issuer attestation.

### Actual disposable Minecraft DEV observations

Run: https://github.com/rinsakamo/relay-self/actions/runs/40267877553

* Platform: pinned Paper 1.21.8 build 60; Mineflayer 4.39.0; Java21,
  Node22 and Python3.12; one loopback isolated World.
* Original first S49 BACK Action: 0.6269065734210615 blocks.
* Original second S49 BACK+SNEAK Action: 0.18807197202631842 blocks.
* Reduction: 0.43883460139474306 blocks, approximately 70%.
* Original S49 terminal Actions: 2/2 OUTCOME. Java and Node exited 0.
* Paper one-shot cap observer: five server callbacks, forward bonus zero.
* Tests: focused Python 3.12, Ruff, Java21 plugin compile, Node install,
  real Minecraft execution and source-linked receipt checks all PASS.
* P1 native state, M0 ledger, SelfBody native sensor, S10 and main were
  **not** modified; no FULL, qualification or scientific trial.

The 0.188m result is one real-world instance, not an absolute cap across
directions, loadouts, TPS or tick phase. It is intentionally slower than
the tentative JOG-speed upper bound, so the precise cap still needs
gameplay calibration. In particular **sideways and forward DASH remain
untested**; Paper attribute updates and Mineflayer physics clocks do not
by themselves attest World-effective motor interval.

## Remaining engineering

1. Add a genuinely authorized forward and sideways S49 Action to the
   existing *single issuer* (not a console-issued substitute).
2. Benchmark RUN vs forward DASH maximum ×1.5 and sideways/backward
   capped output, including stop accuracy across repeated World ticks.
3. Only after actual applied mode and elapsed World time are source-bound,
   integrate once-only additional M0 consumption and one-P1 load−recovery.
4. Do not adopt the previous 0.1m motion prediction-error heuristic as
   intrinsic SelfBody fatigue or physical uncertainty.

This branch is isolated and does not change PR #634, PR #545 or main.
