# Bug-0 P1 sensor threshold sensitivity / one DEV S49 World

The real prospective parent #735 used original pinned P1 model source at
`0ab76b4e46efd914877e543a65de58b6cfc71326`, but with **explicit
nondefault** recovery 0.002/tick. At its real predecision Paper callback
tick176 the model state was **0.045999999999999874**; P1's quantized
virtual observation was **0.05**, just reaching its 0.05 decision threshold.
Thus the REST selection was extremely sensitive to sensor rounding.
It neither observed real Minecraft fatigue nor established a calibrated
threshold.

This child explicitly compares three prospective source-only policies
on the same original predecision Paper log:
1. **Nominal**: quantized reading >= 0.05.
2. **Uncertainty guard**: (reading - quantum/2) >= 0.05.
3. **Predeclared margin**: (reading - quantum/2) >= 0.05 + 0.025.

The last margin 0.025 is deliberately an **unvalidated DEV hypothesis**,
not a P1 rate update or real-world sensory calibration. Original pinned
P1 evaluator and P1 experimental recovery are unchanged.
The S49 existing L0 priority is the only original intent authority;
its predecision `rest_requested` is derived solely from the margin
sensor. A false request results in **normal L0 WAIT**, not an independent
REST Action nor a fabricated REST event.

One fresh disposable Paper 1.21.8 + original S49 process:
- Exactly one original ATTACK/OUTCOME from S49 ActionSupervisor, no retry
  after UNKNOWN or failure. No other Self-issued Action.
- Existing Paper server callbacks from the same original player and
  World expose predecision FIGHT/WAIT candidates. All unknown/foreign/
  gapped/mixed sources fail closed; no postdecision reading.
- Read-only Paper command `s49p1choice nonce WAIT|REST` records actual
  original S49 selected choice separately from prior legacy REST marker.
- Nine subsequent original Mineflayer probes and eight postchoice Paper
  callback ticks must support a **stationary candidate**, not independent
  full-tick inactivity.
- Frozen original P1 evaluator replay compares both default 0.10 and
  experimental 0.002 recovery rates at the exact predecision callback
  tick, and independently recomputes nominal/guard/margin decisions
  from the **same original source**.
- Save full Paper and S49 originals, dual-model comparison, SHA256 manifest.
  Reuse no earlier World and never rewrite or silently retry on failure.
- Existing source lanes P1/M/R/WB, model/Gemma/learning and main unchanged.

**Scope:** DEV_ONLY. A WAIT versus REST *intent* difference does not by
itself demonstrate physiological recovery, survival improvement or learning.
No full-native-R source attestation, true physical P1 fatigue sensor,
calibrated P1 parameters, M basal waiver, QUALIFICATION or SCIENCE.
