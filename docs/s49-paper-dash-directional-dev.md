# Paper 1.21.8 DASH directional cap — isolated actuator DEV

Status: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

The P1 gait model in `experiments/p1_gait_dev.py` now keeps the **DASH
stance** active when lateral/backward input occurs. Both directions
have a provisional **JOG-sized ceiling (4.32m/s)** in the *model*.
They consume no additional DASH M0 cost, and do not receive the
forward-only 1.5× RUN boost. Returning to forward movement does not
require issuing a second DASH activation.

## Isolated Paper actuator candidate

`adapters/mineflayer/s49_paper_dash_dev/` is a **separate, default-OFF**
Paper plugin. It does not change the existing read-only wait observer,
S49 Action authority, original Mineflayer bridge, protected evidence,
or production M0/P1.

Only a DEV console command may arm this actuator. Activation is a
**claim**, not an S49-signed grant: DO NOT place this plugin on a
non-disposable World or claim original S49 end-to-end integration.

- One-shot bounded 40 Paper-tick pilot (2s), not the intended 20s P1
  full-DASH endurance limit.
- Modifier belongs to the plugin's unique NamespacedKey. Uses a
  **transient** MOVEMENT_SPEED modifier of up to +50% while Paper's
  latest input says *forward AND sprint only*, with no side/back/sneak.
- Side/back/diagonal/unknown input does **not** end the DASH state:
  it **removes the forward speed boost** and retains a low-speed stance.
- When PlayerMoveEvent shows movement away from the forward heading,
  it removes the boost and latches the veto until non-forward input
  has been seen; stale forward input alone cannot instantly reboost.
- Stops, timeout, logout, invalid actor, plugin disable and errors
  remove only this plugin's modifier; original attributes untouched.
- Console / UUID / session checks prevent unintended activation,
  but are **NOT cryptographic World source authentication**.

## What is NOT proven

Paper `getCurrentInput()` returns the last provided input, which
might not match actual current movement (especially Mineflayer). An
attribute modifier applies to all directions **while present**; the
per-tick input test and movement veto reduce the risk of lateral/back
boost but do **NOT prove** an instantaneous hard 4.32m/s World speed
cap. Existing velocity, other modifiers and update phasing are not
bounded by this candidate.

There is **no real World run** in this change. Java21/Paper1.21.8
Maven compilation only. To integrate properly: obtain a genuine,
existing single-owner S49 issued **forward DASH** Action, then
bind the Paper actuator to that Action's lifetime, keep original
Minecraft input/control ownership exclusive, and measure World
position changes plus applied speed during straight/side/back
negative controls. Do not modify an existing backward MOVE issued
command to secretly become forward DASH. Map verified applied
World ticks onto the one-P1 fatigue model and the M0 ledger exactly
once. Preserve DEV/QUAL/SCI separation.
