# Bug-0 S49 prospective fatigue-sensitive REST — single DEV World

The preceding real Paper trial (#41837041227 / parent PR #734) recorded
one original S49 ATTACK (Paper server tick100, callback101) followed by
REST intent at server tick167. Default pinned P1 `FIGHT +0.20`,
`WAIT -0.10/tick` reached model fatigue 0 by tick103. The original
default cannot produce positive fatigue at that much later REST decision
from one isolated FIGHT event.

This DEV milestone explicitly tests a **nondefault hypothetical**
recovery rate `WAIT -0.002/tick`, while retaining original P1
`fatigue_p1.py` exact HEAD
`0ab76b4e46efd914877e543a65de58b6cfc71326` unmodified and
evaluating original default 0.10 on the SAME World trace as a comparator.
The alternate rate is not a physiological calibration or an empirical
claim about an animal, zombie or real Minecraft player.

One exact gated disposable Paper 1.21.8 World:
- Original S49 one ActionSupervisor, one ATTACK OUTCOME and source Health
  readback. No repeated ATTACK on any failure or UNKNOWN.
- Operator-only removal of its tagged NoAI target; same S49 owner and
  native player probe.
- **Before** the existing S49 L0 REST decision, a separate read-only
  original P1 model process uses only already-emitted Paper callback
  ticks (one tagged FIGHT event, consecutive source and bounded
  zero-activity candidates) to produce the model sensor and
  `rest_requested` Boolean. The source must not yet contain REST/STOP.
- L0 still applies native food, health, truncation and entity priority;
  no fatigue sensor can mint S49 actions or bypass threat checks.
- Console REST marker and nine native player stillness snapshots are
  recorded later. Original Body sensor/source inputs are not overwritten.
- After Java/Node exit0, an **independent offline replay** on the same
  immutable Paper log compares default and nondefault P1 profiles at
  the original prospective `source_as_of_tick`, and checks positive
  hypothetical fatigue and recovery after REST under the alternate
  profile, but zero under original defaults.

All plugin server tick callbacks are **DEV candidates**, NOT complete
independently R-attested physical WAIT frames. The observed P1 fatigue
remains virtual, and P1 owner live Body state is NOT installed into S49.
No M basal waiver, learning update, qualification or science promotion.
The original Paper log, original S49 report, both profile replay traces
and SHA256 manifest must be retained, including on failure.

A prior draft's physical experiments are never repeated automatically.
This exact message authorizes ONE new DEV World using the explicit
`--bug0-p1-prospective-rest-dev` gate, conditional on negative preflight.
