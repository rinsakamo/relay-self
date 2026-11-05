# WorldBody v1 — fixed World-owned physical limitation, direct SelfBody (DEV)

## Scope and ownership

The **Paper server** owns an actual player locomotor limitation:
- moving consumes an unobservable internal fatigue reserve;
- as fatigue crosses a fixed server-side threshold, Paper invokes
  `Player.setWalkSpeed(0.08f)` instead of `0.20f`;
- while physically stationary, the fixed server-side recovery rule
  gradually restores that reserve; when sufficiently recovered, Paper
  restores `Player.setWalkSpeed(0.20f)`.

These are **DEV World laws** compiled into the separate isolated Paper
plugin `RelayWorldBodyDev`. They are NOT Minecraft vanilla laws, and
are not a live P1 model. The laws intentionally have no command, config
or direct Self-visible setter for fatigue, thresholds, or rates. The
operator-only original Paper server log retains truth snapshots for
post-hoc falsification; **S49 never reads these logs to decide REST**.

This is a basic test constraint, not a physiological claim. Choice
of rate/threshold is made **once at World design time** and is not
changed to force an outcome within the World or between test cases.

## Raw observation → Self's behavior, without a new sensation engine

1. The original S49 host/session/ActionSupervisor handles two ordinary
   admitted MOVE_BACKWARD Actions under natural near-zombie L0 stimuli;
   each S16 OUTCOME must be genuine. No direct command authorizes MOVE.
2. After each S16, the owner projects the native after-Present using
   the existing `self_body_projection` and `SelfBodyView`. It reads
   measured action displacement from that original S16.
3. An independent, explicitly temporary L0 DEV rule compares first
   and second measured move distance. If the second is less than 80%
   of the first, it **requests REST**. This is a simple observed-loss
   rule, not a fatigue sensor or learned Goal system.
4. The original S49 `S49BasicPriorityL0` checks a fresh native
   Present; a nearby threat, insufficient coverage or health gate
   can still block REST. The operator clears staged zombies to
   open a safe test interval.
5. If REST is selected, S49 issues no further physical Action. Nine
   independent Mineflayer native stationary probes cover about
   32 seconds. WorldBody's original Paper tick scheduler continues
   physically recovering according to its precompiled law.
6. A **post-World-only operator auditor** reads the original Paper
   internal log (never consumed as a Self sensor), checks degraded
   and restored actual walk speeds and the S16 movement loss, and
   stores original source hashes.

The result is not Goal learning, a calibrated bodily sensation or
a full test of post-REST locomotor improvement. Observing a third
real MOVE after recovery is intentionally the next milestone;
S49 original Action admission and post-movement settling require
care before expanding from the existing two-MOVE owner.

## Hard boundaries

- WorldBody is server-owned; SelfBody does not receive true fatigue,
  fatigue rates, speed thresholds, or server internal logs.
- SelfBody retains native Present and S16 outcome provenance.
- REST is a decision, not a self-authorized physical-action/energy waiver.
- Existing P1 experiment, M lane, L lane, WB cognition, original S49
  owner, and main remain unchanged.
- Any original World test uses a disposable pinned Paper 1.21.8 World,
  explicit one-time commit grant, no automatic retry and SHA originals.
- DEV_ONLY; QUALIFICATION_NO_GO; SCIENCE_NOT_RUN.

### Deliberate limitations

This is a simulated **WorldBody constraint** added to Minecraft,
not evidence that actual human fatigue is captured by this model.
The internal fatigue value is observable to the external *scientific
auditor* from the Paper server log, not to the Self; if that log is
ever passed into Self's L0 decision path, the experiment is invalid.

If Paper server movement speed changes but Mineflayer's measured
movement per admitted Action does not change, **the behavioral
test is a failure**. Do not call it a success merely because the
server-side API reported a different speed.
