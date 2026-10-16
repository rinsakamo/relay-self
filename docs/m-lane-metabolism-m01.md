# M0.1 — Minecraft-tick metabolic accounting, candidate ecology (Issue #616)

**Status: OFFLINE PHYSICS CHARACTERIZATION ONLY / ECOLOGICAL CALIBRATION PENDING.**
Existing M0 `experiments/metabolism_viability.py` and its successful B0 producer/Golden
source remain immutable. M0.1 is an opt-in **additive** proposal in
`experiments/metabolism_m01_minecraft.py`; nothing imports it into S51/B0 yet.
M0.1 replaces neither Minecraft food/hunger/health nor S/R-owned Action authority.

## What is and is not “realistic”

An invariant model can be unrealistic. To support ecological generalization,
**relative** costs and food-opportunity dynamics require separate calibration:
meal-supported idle duration, reserve-supported idle duration, locomotion-to-basal
power, search-trip cost/food value, encounter/replenishment rate, food toxicity,
exposure/predator hazard, and source-available sensory information.
**Do not fit ratios by selecting only the L1 policy that survives.** Historical
M2 cheap-cue dominance and B0’s fixed hunger threshold are counterexamples to
claiming adaptive cognition from survival alone. A realistically calibrated body
also does not by itself create learned hunger or value.

`ecological_ratios` returns descriptive units/ratios, no “good” label or learned
threshold. Candidate coefficients are **not** real-world biological constants;
they must be explicitly named and frozen with their evidence and uncertainty.
External anchors can include measured Minecraft 1.21.8 food/World motion and
foraging-ecology literature. Charnov (1976), *Optimal foraging, the marginal
value theorem*, DOI 10.1016/0040-5809(76)90040-X, frames travel/patch payoff
as ecological constraints but does not provide universal species-independent
numeric coefficients. A reference ecology (e.g. small low-cognition scavenger)
must be specified before selection of candidate coefficient ranges.

Minecraft rotten flesh is documented to restore 4 hunger points and 0.8
saturation with a substantial Hunger-effect risk. **4 hunger points are not
4 M0 energy units.** The previous M0 `food_energy=4` is an experimental
convention, not a conversion proof. If the World native source does not attest
the Hunger effect/duration, a positive S51 eat receipt may be admitted as an
abstract energy-event candidate but never as proven **net** ecological gain.
Documented Minecraft gameplay data is *not* actual calorimetry.

## Offline M0.1 physical contract

- `WorldTickSample.world_tick` is a monotonic **world age** (1 tick increment),
  never time-of-day (which wraps), host wall-clock, number of L0 decisions, or
  number of requests. Every next sample must be consecutive and same session.
  Gaps, uncertain clocks, unusual displacement, and unobserved tick movement
  **reject** instead of guessing or charging extra per decision. This version
  intentionally cannot handle sparse real Mineflayer sampling without a new
  S/R-qualified dense producer or separately attested cumulative motion.
- `xyz` represents one real position per World tick. One-tick Euclidean delta is
  a bounded *proxy* for traveled path length. Loops inside a tick, teleportation,
  vehicles, jumping/external forces and nonuniform terrain are NOT characterized.
  A configurable upper bound rejects implausible deltas but does not authenticate
  a source. Do not mislabel this proxy as mechanically measured work.
- Verified consumption **event identity**, item count decrease, Minecraft food
  meter increase, same session, and source Action ID are prerequisites. The
  `AdmittedFood` type checks a caller's evidence shape but is not a signature:
  only the independent S/R owner may admit original frames. Repeated action ID
  cannot mint more energy. Pickup alone does not mint any energy.
- Per consecutive tick, apply food intake first, clamp to capacity (record
  overflow), pay basal and measured motion cost; at energy <= 0 terminate
  irreversibly and track any unpaid shortfall. Cumulative balance identity:
  `E0 + intake - basal - movement - overflow + shortfall == E_now`.
- All true energy and inputs are on evaluator/M side. Do not leak `state.energy`
  or metabolic rate to L1; M0 `observe_energy` or independently justified sensor
  projection remains the only Self-accessible route.
- No Action authority, training objective, reward, pleasure/pain, evolution,
  resource regeneration, fight-energy formula, food-poison side effect, real
  Minecraft execution, or production wiring is created in this milestone.

## Calibration gate before learning

1. Select a reference ecology and declare food resources/encounter rates,
   threat exposure and World tick cadence. Reference information must not
   supply an Action oracle to Self.
2. Record independently justified candidate **ranges** for metabolic tick rate,
   locomotion cost per block, storage capacity and food-specific *net* intake,
   including uncertainty and missing Minecraft status effects. Reject
   unidentifiable parameters rather than backfitting good-looking Self behavior.
3. Freeze profile IDs, ratios, World schedule and test seeds before comparing
   policies. Check: no-food terminal, positive net intake where applicable,
   sensible food-search roundtrip break-even, affordable/rest-limited activity,
   plausible reserve/meal-supported durations, stability to observation
   frequency and World-time acceleration, and known cases where a cheap
   WAIT/SEEK policy wins. Record ecological nulls and impossible conditions.
4. Separately obtain S/R-native `world_age` and adequate movement evidence,
   hunger-effect status, and real outcome identity before any **DEV** World
   integration. DEV remains DEV_ONLY. A new R run qualifies the new physics
   separately; B0 historical `B0_RSEE_ENGINEERING_QUALIFIED` cannot be reused
   as M0.1 qualification. V controls scientific comparison and stop rules.

## Minimal local verification

```bash
PYTHONPATH=. python -m pytest -q tests/test_metabolism_m01_minecraft.py
```

Regression tests require legacy `experiments/metabolism_viability.py` bytes
unchanged, no import into the S51 production path, no grants or World starts.
Classification after this offline code only:
`M01_OFFLINE_WORLD_TICK_LEDGER_TESTED / ECOLOGICAL_RATIOS_DESCRIPTIVE /
SOURCE_ADMISSION_NOT_DONE / PHYSICAL_WORLD_NOT_RUN / SCIENCE_NO_GO`.
