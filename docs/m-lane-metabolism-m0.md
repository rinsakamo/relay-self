# M Lane M0 — Energy, terminal starvation, and interoception (Issue #616)

**Status:** experimental offline mechanics only. These files neither implement an
agent's reward function nor qualify Minecraft, physical LLM actions, evolutionary
improvement, affect, subjective experience, or production use.

## Reconciliation with existing RelaySelf

- `experiments/evolved_values.py` (#42) **already** simulates basal/action
  metabolism, food, inherited reward coefficients, Q-learning, mutation and
  reproduction. This remains the evolution reference. It provides
  `nearest_food_direction` to its controller and has a `maximum_age` termination,
  so its existing outcome **does not** establish the proposed interoceptive,
  starvation-only Colosseum condition. Do not replace/reinterpret its evidence.
- The historical Mineflayer viability-gradient #46 is NON_DISCRIMINATING;
  explicit signed gradients alone are not scientific evidence of learned value.
- #265's emotion-like trajectory/attractor interpretation is downstream and
  cannot be hardcoded as an M Lane objective.
- The S Lane owns Action/World/feedback integration; R Lane owns RSEE/Minecraft
  laboratory and authentic World evidence; L Lane owns learning/retention;
  V Lane independently determines scientific validity. M0 writes to none of these.

## Proposed physical/evaluation contract

`experiments/metabolism_viability.py` is a **pure offline example** of one narrow
physics/observation separation, not a competing host or simulation engine.

- **One tick:** already-verified food intake is credited, capped at energy
  capacity; then mandatory basal cost and action cost are deducted. At energy
  `<= 0`, the terminal flag becomes true, remaining energy is set to zero, and
  no further ticks/respawns are allowed. The intake-before-cost order is a
  deliberate convention and must be retested against any real-world binding.
- **Waiting is not free:** positive basal cost applies under `WAIT` as well as
  `MOVE`/`FIGHT`. A zero-food policy with finite initial energy terminates in
  finite time. This is *not* a prediction that every agent ignoring its energy
  necessarily eats zero food; an unguided/random agent might incidentally eat.
- **Combat knockout is not permanent death:** `combat_respawn()` records a
  knockout without resetting time, energy, meals or any external memory. It
  cannot revive a starved agent. Real HP/food inventory are **not simulated**.
- **True E versus sensed E:** `BodyState.energy` belongs to the evaluator;
  `observe_energy` emits only a gain/bias/quantized `EnergyObservation`.
  Interoceptive `gain=0` erases variation. This is not yet an inherited gene,
  learned valuation, noisy sensor or authenticated runtime privacy barrier.
- **Input provenance:** `consumed_food_units` is required to be a **verified**
  world-consumption count supplied by the caller. The pure function cannot
  attest that provenance, so an arbitrary integer passed from an agent must
  never become a real energy gain in production. S/R authentic evidence is a
  prerequisite for such a bridge.
- **No reward or fitness:** the step emits only physical energy intake, costs,
  overflow, starvation and observables. It never supplies `GOOD`/`BAD`,
  `pleasure`, `pain`, a food bonus, reproduction pressure or a learning target.

## Scientific gates after M0

1. **M1:** compare blind/gain-variant sensing, memory/learning ON-OFF, a
   fixed cheap eater and stochastic/no-op policies in paired resource sequences.
   Classify whether any nontrivial incremental causal learning exists.
2. **M2:** reuse #42 evolution machinery with *explicit* sensor and control
   predisposition inheritance, lineage/offspring fitness and no-selection
   controls. Replacing maximum-age mortality with starvation-only death is a
   separate experimental condition, not historical #42 evidence.
3. **Colosseum/RSEE:** only after independent R/S/V admissions, map authentic
   Minecraft consumption to energy intake and HP defeat to knockout. Keep
   configurable per-tick world/real-time rate, freeze food/weapon/enemy schedules,
   and preserve the energy ledger across respawns.

No new semantic owner or physical grant follows from passing these offline tests.
