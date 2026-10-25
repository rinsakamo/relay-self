# RelaySelf — SelfBody Motion Feedback v0: first real closed loop (DEV)

**Date:** 2026-10-25. **Status:**
`DEV_REAL_S49_SELF_BODY_MOTION_CLOSED_LOOP / DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Intention and safety boundary

SelfBody has a bounded, updateable estimate of how much this body
moves in response to a requested control hold. Its input is the original
S49/S16 **already terminal** WorldConsequence with exact decoded
Mineflayer BEFORE, effect ACK, cleanup ACK, and AFTER frames. Source
provenance and X/Z displacement are independently validated by the
existing `capture_native_action_evidence()`.

- `SelfBodyMotionState.observe_closed()`: per-session immutable
  action-derived samples, requested hold seconds, observed movement,
  previous predicted movement and error. No additional native reader
  or probe; samples from the original S16 callback **after** closure.
- `propose_motion_correction()`: DEV-configured **0.45-block target**
  (not claimed as original S42 L0 intent), first three native Action
  samples, imperfect estimate of displacement/requested host second,
  and 25% single-action step bound. No causally inferred fatigue,
  motor physiology or R source-bound tick.
- `apply_to_next_issued()`: duration-only, pure copy of the already
  S14/S16-approved original Mineflayer command, preserving action ID,
  binding, cleanup and sole original executor. Fails closed on foreign
  source, stale sequence, already-used action, modified command, no
  evidence, unattested permissions or duration bounds.
- Original S49's action authority/L0 chooser and original S15
  `execution.py` and P1 `fatigue_p1.py` **not changed**. The
  isolated Paper DEV runner additionally opts into
  `--selfbody-motion-feedback` after the existing six-epoch
  opt-ins, **original model only**, explicitly disabled by default.
  There is no independent Action issuer, reading task, recurrent
  in-Action correction, retry, S10 update or external R/V adoption.

For simplicity the predictor uses total native observed displacement
divided by **requested** control-hold seconds, not actual actuation
time or true Minecraft World tick count. It should be treated as an
uncertain empirical interface, not a physical-body calibration.

## Verifiable real Minecraft outcome

Fresh disposable Paper 1.21.8 Java 21 / Node 22, Python 3.12,
original S49 session, **six actual L0 decisions / four original S16
`OUTCOME` MOVEs**, original Java/Node exit **0/0**.

[Successful exact-head Actions run #40185745453](https://github.com/rinsakamo/relay-self/actions/runs/40185745453)
on commit `31742d1196afdfbbfb9eacf8f66df27bb99bc840`.
[Downloadable original ZIP artifact #12595403705](https://github.com/rinsakamo/relay-self/actions/runs/40185745453/artifacts/12595403705)
was downloaded and inspected: `original_s49_report.json`,
`world_first_dev_report.json`, `paper_server.log`,
`paper_observer_window.log`; original and outer statuses both PASS.

- Same original session:
  `66ad925f-411f-46c8-9eb0-66ae5463d6a9`.
- Original first three actual native S16 MOVE distances:
  `0.626906573421061`,
  `0.6269065734210615`,
  `0.6269065734210613` blocks. Each Action nominal hold request
  `0.200` second; Action IDs `s49-native-move-19`,
  `s49-native-move-49`, `s49-native-move-73`. Strict terminal
  source lineage.
- Before sixth-epoch original S49 action: SelfBody estimated
  `3.134532867105306 blocks / requested second`. Existing P1
  hypothetical duration `0.19648932318884205s`; predicted
  displacement `0.6159022415707022` blocks, DEV target `0.45`.
- Bounded 25% reduction, issued original S49 sixth Action command
  duration **`0.14736699239163153s`**. Predicted displacement
  `0.4619266811780266` blocks.
- Fourth original S16 **`s49-native-move-100`** completed successfully.
  Native before seq102 / after seq108 and after observed displacement
  **`0.4302315371625086` blocks**. Observed target error
  **`-0.019768462837491396`** blocks. Closed sample retains
  prediction error `-0.031695144015517984` blocks.
- Updated SelfBody after fourth S16 has **four samples**,
  including corrected actual issued duration. No new process/read
  owner; original cleanup Java exit0, Node exit0.
- Python3.12 touched focused tests; negative cases for foreign
  source, stale/duplicate frames, forged and missing native
  evidence, forbidden permission claims, unbounded duration and
  early opt-in; Ruff and Java observer JAR build: all PASS.

**Evidence strength:** successful existence demonstration of the
one-way closed loop with actual S49 Action outcomes. It is **one new
World**, not a paired randomized trial or evidence that correction
generalizes or is closer than uncorrected control across runs.
There was no source-bound WorldTick, actual physical fatigue sensor,
P1 motor calibration, S10 learning or SCIENCE.

## Failed checks and resolved edits

Immutable earlier workflow attempts are kept:

1. [#40185331585](https://github.com/rinsakamo/relay-self/actions/runs/40185331585)
   PREWORLD test fixtures incorrectly tried to set
   `MineflayerObservation.provenance`, which is a derived property.
2. [#40185471461](https://github.com/rinsakamo/relay-self/actions/runs/40185471461)
   PREWORLD negative control used `rejected` without protocol-required
   error; original typed protocol correctly refused it.
3. [#40185598045](https://github.com/rinsakamo/relay-self/actions/runs/40185598045)
   PREWORLD Ruff found one unused fixture variable.
4. Fixed and narrowed focused tests in #40185745453: all checks
   and the real World closed-loop PASS. No earlier failures
   reclassified as a PASS, no new World run in failed checks.

Protected original `normal_action.py` blob
`0ded8fa296c92076a643de08cd6fc360061e1d08`;
original `fatigue_p1.py` blob
`bd4f35a4079da0770ef11cdec921dbba31de9b81`, unchanged.

Branch `self/dev-selfbody-motion-feedback-v0-20261025` is
DEV-isolated. **Draft PR #545/#634 and main untouched.**
Adopting historic DEV original S49 runner changes requires a
separate owner/source review; this DEV result is not R QUALIFICATION
or V SCIENCE.

## Next practical step

Measure Node input-ON/OFF monotonic times and Mineflayer physicsTick
indices, with read-only Paper World tick snapshots, without
conflating local physics ticks with R-attested server-effective
control ticks. Then evaluate whether a bounded tick-step actuator
controls distance more consistently than a millisecond rescaling.
Do not raise R/SCIENCE evidence requirements for this DEV iteration.
