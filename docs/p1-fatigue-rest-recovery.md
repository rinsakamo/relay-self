# P1-A — Fatigue, REST & physical capacity (offline)

**Authority:** #620 solo-first P1; M #616, S #537, R #575, V #619.  
**Classification:** `P1_A_DETERMINISTIC_BODY_PRIMITIVE / DEV_OFFLINE_ONLY / S_R_BRIDGE_NOT_INSTALLED / SCIENCE_NO_GO`.

## Independence: Minecraft exhaustion is NOT fatigue

M0.2 (`experiments/metabolism_m02_exhaustion.py` and M0.2 Paper DEV) controls **Minecraft hunger/exhaustion/saturation**, with the server as the physical authority. Its `BASAL` charge is per actual World tick and `WALK` per measured **actual** block displacement; the native Paper event count is *not* a centimeter counter. M0/M0.1 are separate historical energy simulation contracts. **Do not double-bill food/exhaustion**, create another energy ledger, overwrite those originals, or equate virtual fatigue with either Minecraft hunger or physiological exhaustion.

P1-A adds `experiments/fatigue_p1.py` only: an opt-in, evaluator-only virtual Fatigue state (dimensionless units). No Paper listener, Action/Skill/Memory grant, autonomous REST policy, new launcher, L1/L2 learning or cognitive cost. In particular it does not change native movement or fight outcomes until an S/R-owned bridge **applies** the mechanical envelope.

## Exact reference physics (candidate, uncalibrated)

- `enabled=False` default; OFF state remains at zero and capability remains 1.0 under WAIT/REST/MOVE/FIGHT. Historical M0/M0.2 behavior is not modified.
- One **consecutive World tick** per `FatigueFrame`. State stores session ID, frozen profile SHA256, tick and true `fatigue`; invalid/missing/repeated ticks fail closed. Actions/decision count/wall time never fabricate ticks.
- Fatigue range `[0, capacity=1.0]`, initial `0.0`. `MOVE` accumulates actual source-attested **blocks** × `move_per_block` (candidate `0.04/block`); `FIGHT` accumulates observed fight events × `fight_per_event` (`0.2/event`, 0 or 1 accepted per frame). A blocked MOVE with 0 measured movement incurs zero distance-linked accumulation; partial movement incurs fatigue for the actual distance, not for a nominal command. This does **not** model isometric effort against an obstacle.
- `REST` recovers `0.10/tick` down to zero; `WAIT` neither recovers nor accumulates. Both still occupy a World tick and **must incur M0/M0.2 basal energy cost through the existing owner**, just as no physical action can pause server metabolism. `REST` is a prospective separate Self intent, **not an already issued/authorized Action**. Frame shaping alone does not prove a genuine World rest interval.
- Every rate, including movement, combat, recovery, and impairment, is editable as `standard × multiplier + additional`, with explicit standard in the `FatigueProfile`. Reject NaN, infinity, negative rates and changed profile SHA during a session. No cognitive consumption bridge (default OFF).
- Evaluator-only `BodyCapability` reports efficiency `clamp(1 - (impairment_rate × fatigue / capacity), minimum_efficiency, 1)`, by default impairment `0.7`, minimum `0.2`. The maximum nominal travel in one World tick is `1 block × efficiency`; one simulated FIGHT becomes mechanically infeasible below an editable efficiency threshold (`0.5`). These are **Body limits**, not a policy, authorization, actual measured displacement, or evidence of a successful BLOCK/FIGHT. They must be enforced prospectively in a World bridge before claiming behavioral effects.
- Transition receipt contains before and after private state, the input frame, actual bounded accumulation/recovery, and capability before/after. This is **deterministic offline provenance**, not an authenticated original Minecraft event. Keep the full receipt evaluator-only.
- `observe` produces separately typed quantized fatigue reading; gain=0 masks true variation. Do not pass FatigueState or transition to an L0/L1/L2 controller.

## P1-B handoff (not implemented by P1-A)

1. **S #537:** define new REST intent/observation and source-backed elapsed tick interval with existing Action authorization, without pretending nonissued WAIT is an Action. Apply Body capability **before** one-block S50 steering or combat to constrain actual motion/outcome. L0 safety, if needed, must be explicitly labeled engineered. Do not install an optimal REST heuristic in P1.
2. **R #575:** use existing solo-enabled disposable DEV World, block all autonomous entities (including animals/villagers, hostiles and summoned mobs), attest negative entity census with snapshot coverage; do not treat no-entity observations under incomplete coverage as solo. Preserve zombie regression tests separately. Pin session / World tick / source of measured block motion / tick gaps / cleanup. Source-attest REST intervals, not action counters.
3. **M #616:** BASAL continues every World tick during REST. M0.2 Paper server is single source for hunger/saturation/health; do not apply M0.1/M0 energy debit in that World. Energy and Fatigue advance independently and are compared by identical World tick. Consider partial movements, barriers and too-fast motion as provenance/admission concerns, not distance predictions.
4. **V #619:** preregister Fatigue OFF, Fatigue ON + explicit cheap L0 rest, ON + L1, ON + L2, with fixed-rate/finite-state alternatives and source-matched cost accounting. Freeze sample sizes, stopping rules, seeds, null retention, energy, fatigue, rest time, success rate, activity, compute cost before any SCIENCE. No uplift claim from this module.

## Mechanical limitations / next tasks

- The pure function **does not enforce** movement limits in live Minecraft; S/R bridge is missing. It computes and exposes testable capacity constraints that prospective World execution must enforce; no P1 behavioral validity until then.
- An observer must not infer `blocked` from distance alone; it is a separately authenticated outcome label, and is not charged as successful travel. In-place attempted movement cost / combat effort before hit is outside P1-A.
- Current candidate rates and fight threshold are intentionally artificial; biological fatigue is not measured. State cannot be promoted to observed physiology, learned action policy, adaptive benefit or scientific success.

## Offline checks

`python -m pytest -q tests/test_fatigue_p1.py` — deterministic OFF, distance source, partial/blocked, REST/WAIT, finite bounds, capability threshold, session/tick/profile fences, sensor blindness, metabolic noninterference. Source stack: current M Draft #617 exact branch at fork; changes only the three new P1 paths. Existing Drafts and protected main are untouched.