# P1 DASH physical motor — Paper / Mineflayer disposable DEV

Classification: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Branch: self/dev-p1-forward-dash-paper-20261025

## Agreed compressed-World design

WALK = vanilla sneak, JOG = vanilla walking, RUN = vanilla sprint,
DASH = forward-only sprint plus a bounded temporary speed multiplier.

Max DASH nominally RUN x1.5. Power from 1 to 100% selects modifier
gain=0.5*power. The Paper plugin limits one shot to at most 400 World
ticks; this real DEV motor exercise is only 0.65 host seconds per Action.

The one-state P1 net load-minus-recovery model lives in
experiments/p1_gait_dev.py. Full DASH 20 s until fatigue exhaustion
is currently a **pure hypothetical model**, not real Paper enforcement.

## Implemented

1. Dedicated Java21 Paper 1.21.8 plugin in
   adapters/mineflayer/p1_dash_paper_dev:
   console-only one-shot relaydashdev arm/off, forward+sprint gate,
   dedicated transient MOVEMENT_SPEED modifier, removal on OFF/logout/
   onDisable/expiration. Existing Paper observer remains read-only.

2. Paper PlayerInputEvent was ineffective in Mineflayer 4.39.0. The
   plugin thus uses an explicitly WEAKER DEV fallback: recent actual
   PlayerMoveEvent positive motion projected along the player's facing.
   Backwards/sideways evidence revokes the modifier at next monitor
   tick. This is NOT full input-edge attestation or zero-latency stop.

3. Isolated temporary client physics DEV patch in
   adapters/mineflayer/p1_dash_native_physics_dev.py clones the original
   bridge.mjs into a sibling ESM. It matches the server +0.50 speed
   modifier only for a specifically named operator-DASH sprint command,
   and restores it on clear / shutdown. The protected bridge remains
   unchanged, and there is exactly one Node/Mineflayer process.

4. Real Paper + Mineflayer runner in
   adapters/mineflayer/p1_dash_paper_real_dev.py compares baseline RUN
   and 100% DASH, collects Paper fullTime-labeled native position
   snapshots, checks exit and modifier removal, and requires a higher
   actual sustained per-tick movement speed, not merely API success.

## Experiments

- https://github.com/rinsakamo/relay-self/actions/runs/40202340559
  PREVIOUS FAILED DEV: no observed Paper forward input, zero applied
  modifier ticks. Native motion itself succeeded; not DASH.
- https://github.com/rinsakamo/relay-self/actions/runs/40202645472
  Paper speed modifier attached during 13 ticks and removed, but client
  actual forward speed plateaued at about 0.28m/tick: still ordinary RUN.
  The baseline/DASH action displacement ratio did not prove a boost.
- https://github.com/rinsakamo/relay-self/actions/runs/40203303714
  PASS: after syncing Mineflayer physics, the Paper final-five-active-tick
  average was **0.4201887665m/tick (8.403775331m/s)** vs the nominal
  RUN speed 0.2805m/tick (5.61m/s): about **1.498x**.
  Node and Paper exited with code 0; 13 server active movement samples,
  removal of transient modifier attested.

The whole-action displacement ratio (5.406m / 2.082m) is NOT an
intrinsic speed multiplier: starting motion and acceleration differed.

Observed Paper movement callbacks do not prove full-World-tick input
intervals. Hypothetical one-P1 fatigue value 0.03917698 and extra M0
charge 0.13 from 13 callbacks were neither physically admitted nor
posted to M0/P1 ledgers.

## Epistemic / authorization boundary

This is an operator-controlled DEV motor apparatus in a disposable
World. It has no new S Action grant and is **NOT** an original S49
authorized forward Action. It is not QUALIFICATION or SCIENCE.

Next integration must use a **legitimately authorized S49 forward
Action on the original single-owner/single-receiver path**, compare
negative lateral/backward inputs, and correlate whole-tick World
activity before any physical M0/P1 ledger writes. The prior arbitrary
0.10m SelfBody uncertainty damping is not adopted.
