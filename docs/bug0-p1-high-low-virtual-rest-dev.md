# Bug-0 P1 — high-virtual-fatigue REST versus low-virtual-fatigue WAIT (DEV)

## Prior low profile (physical World #41927124487)

The single original S49 ATTACK hit an externally staged tagged zombie
(Paper Health 20.00→19.06); **same** original player/session had a
predecision Paper tick177 and exactly one FIGHT callback. Unmodified
original P1 `fatigue_p1.py` commit
`0ab76b4e46efd914877e543a65de58b6cfc71326` was evaluated
under an explicitly experimental rate `WAIT recovery 0.002 per callback
tick`. Virtual fatigue 0.048 quantized to 0.05; the predeclared margin
rule `reading - quantum/2 >= 0.05 + 0.025` rejected REST and existing
S49 L0 selected **WAIT**. Real World #41927124487 PASS; physical
fatigue was not measured.

## New high profile

Use the identical pinned original P1 evaluator, capacity, FIGHT +0.20,
interoception quantum 0.01, and conservative margin threshold.
**Only** change the explicit, uncalibrated profile's WAIT-recovery
rate to `0.001 per candidate callback tick`. For a one-FIGHT and
~76-WAIT Paper prefix, this predicts approximately virtual fatigue
0.124 and model sensor value near 0.12, well above the policy's ~0.08
quantized decision boundary. The first (0.002) profile predicts
~0.048 and WAIT for the **same read-only Paper prefix**.

The difference is **hypothetical Body metabolic parameters**, NOT
independently measured differences in Minecraft exercise or fatigue.
Do not silently present these as a learned response to the environment.
The precise dynamics may change with actual observed Paper callback
tick count: any unexpected preflight activity fails closed.

One new source-bound original S49 real World is allowed only by
exclusive `--bug0-p1-high-dev` and
`S49_BUG0_P1_HIGH_DEV_ONLY=1` plus previous explicit Paper gates.
The original S49 ActionSupervisor issues *one* ATTACK. A late unknown
outcome is not retried. The server-only source publisher records a
single event FIGHT and monotone scheduler callbacks. A separate
original-P1 subprocess evaluates predecision callbacks only.
The resulting high-profile request enters **existing original L0**
which can select REST only if food/threat/health/coverage priorities
permit it. REST issues **zero** extra native Actions.

Native Paper `S49P1_CHOICE selected=REST`, nine existing Mineflayer
stillness probes and eight future native callback candidate ticks
are retrospective *evidence*, never inputs to that earlier L0.
A post-World replay checks the original exact P1 model and same
Paper event source, restoring both default profile (0.10/tick)
and high experimental profile (0.001/tick); reports original
S49 World/session/action/health and SHA256 originals.

No physical P1 sensor, no calibration, no independent R/S full-tick
activity attestation, no M basal credit, no durable learning,
no QUALIFICATION/SCIENCE claims. Main and all parallel lanes stay
untouched.

This is a deliberately bounded DEV test of the high **virtual** fatigue
branch versus the prior real low-virtual-fatigue WAIT branch, not a
demonstration of bodily adaptation or better survival.
