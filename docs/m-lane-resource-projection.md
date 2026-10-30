# M1 resource quotation — DEV/OFFLINE read-only candidate interface

Owner: M #616. Branch `research/m616-m1-resource-cost-projection-20261030`
starts from frozen P1 Draft #626 HEAD `56600977fb730918ac67769df0ad9ab45f2e9d49`
to reuse M0/M0.1/M0.2/P1 exactly, without writing to that Draft.

## Current boundary

- `experiments/metabolism_resource_projection.py` creates bounded
  **hypothetical** candidate costs from existing `M01Profile/M01State`.
  `WAIT` pays basal each future tick. `MOVE` pays basal per tick and
  movement cost per projected block. Costs depend on supplied nominal speed,
  not on Action request success.
- When provided, existing P1 `capability()` and `advance()` project
  fatigue/motion limits. A blocked zero-displacement MOVE is still MOVE,
  never a WAIT-recovery event. This creates no P1 physical ledger update.
- An unknown route/speed, excess horizon or unmodeled gait is `UNKNOWN`.
  The projection assumes no future EAT credit, World discovery, combat
  hazard or obstacles, and does not make new Action choices.
- `ResourceQuote` is **evaluator-private**: it may contain physical true
  energy and a conditional exhaustibility result. The `visible_costs()`
  projection exposes only the already supplied owner interoception reading,
  candidate costs and uncertainty, not true energy, physical feasibility
  or subjective wants. Actual SelfBody integration remains #632/#634.
- `quote_m02_exhaustion()` computes a separate hypothetical Minecraft
  exhaustion-unit estimate using the existing M0.2 source profile. Explicit
  WALK/SPRINT mapping is mandatory for land movement; JOG/DASH are NOT
  silently mapped. The M0.2 result MUST NOT be added to M0/M0.1 Energy.
  It cannot determine native food, saturation, HP or terminal survival.
- All candidates are read-only, source **UNATTESTED** and
  `OFFLINE_ONLY`. No food acquisition, eating/credit, WorldTick admission,
  native source trust, Action issuance, learning, reward or death policy
  has been added.

## Test gates

The focused suite covers basal during WAIT, P1 recovery independent of
Energy, actual distance vs issued Action, hypothetical exhaustion boundary,
blocked MOVE, missing route/speed, horizon, source/session/tick fences,
sensor leakage and M0.2 unit isolation. Existing M0/M0.1/M0.2/P1
characterization remains authoritative for food deduplication, terminal
exactly-once, and tick-source accounting; this module does not replace them.

Run Python 3.12:

```sh
python -m pytest -q tests/test_metabolism_viability_experiment.py \
  tests/test_metabolism_m01_minecraft.py tests/test_metabolism_m02_exhaustion.py \
  tests/test_fatigue_p1.py tests/test_metabolism_resource_projection.py
ruff check experiments/metabolism_resource_projection.py tests/test_metabolism_resource_projection.py
```

No real World/GPU, R qualification, independent V scientific efficacy,
or product integration is claimed. M2 #621 and P1 #626 stay unchanged.

## M1 sensor-conditioned read-only affordability (2026-10-30 extension)

`experiments/metabolism_sensed_viability.py` reads **only**
`SelfBodyResourceCosts` (a pre-existing M-produced observation/cost view),
the public M0.1 profile capacity, and an `Interoception` calibration.
It does not accept `M01State`, `ResourceQuote`, true physical Energy,
future food credits, native World outcomes or policy callbacks.

For a quantized reading `r`, sensor gain `g > 0`, bias `b`,
quantum `q` and separately bounded absolute sensor noise `n`, the
**hypothetical** Energy interval is the capacity-clipped inverse
`[(r-b-q/2-n)/g, (r-b+q/2+n)/g]`, outward rounded for floating
point. This inversion is valid *only if* the supplied M0 quantization
and finite noise bound are accepted assumptions. If `g = 0`,
no noise bound is supplied, or the range contradicts body capacity,
the interval is UNKNOWN. Gaussian/unbounded M1 sensor noise must be
represented as UNKNOWN, never arbitrarily bounded by its sigma.

For a cost quote `C`, the model-only classifications are:
- `MODEL_AFFORDABLE` if **every** sensor-consistent Energy exceeds `C`;
- `MODEL_INSUFFICIENT` if **every** sensor-consistent Energy is
  at most `C` (M0.1 terminal at exact zero);
- `MODEL_AMBIGUOUS` otherwise; `UNKNOWN` for unknown cost or sensor.
These are conditional tests of a bounded *model*, NOT true resource
guarantees or an Action recommendation. Route hazards, collisions,
unqualified gait application, unseen food and physical native hunger
remain outside the estimate. Nothing is automatically selected.

**Cheap null / counterexample:** a zero-gain blind sensor produces
exactly the same reading for high/low true Energy and thus UNKNOWN
for both conditions. A known deterministic gain=1/quantum=1 sensor
plus a hypothetical 5-block move costing 2.5 M0.1 units classifies
sensed 8.0 as model-affordable and sensed 1.0 as model-insufficient.
The same cost is passed in both worlds; this is representation
sensitivity, **not a learned choice or an observed survival lift**.
Quantization boundary and bounded/unbounded noise ablations retain
ambiguity instead of inventing a preference.

**Current G4 / P1 source boundary:** [G4.13 DEV](https://github.com/rinsakamo/relay-self/blob/1d1b16349a7e13bebd4081a0ca53d9c2be227573/docs/s49-g413-original-g1-witness-real-paper-dev-20261030.md)
reports a controlled-world 133 T2/P1/M0 tick receipt join but 123
original G4.9 gait observations remain UNKNOWN; frame co-occurrence
does not qualify exact applied gait, and no per-gait Energy multiplier
is inferred here. [T1s](https://github.com/rinsakamo/relay-self/blob/946708c2daab0741b34f3b669efafb4622262a43/docs/t1s-native-dev-results-20261028.md)
tested a later P1 recalibration in DEV, **not present in this branch's
inherited P1 Draft #626**. The model in this branch invokes precisely
the inherited P1 implementation. M never substitutes T1s coefficients
or treats physical `exhaustion` as virtual M0.1 Energy.

`tests/test_metabolism_sensed_viability.py` exercises same-World
high/low Energy, blind sensor null, coarse quantization, unknown and
bounded noise, inconsistent reading, unknown route, WAIT basal and
foreign producer inputs. Only these OFFLINE representations are in
scope. SelfBody #632/#634, L, G, S and R remain independent owners.

## M1 route envelope extension (2026-10-30)

The new `experiments/metabolism_route_bounds.py` calculates a read-only
interval for travel to a GOAL or FOOD_OPPORTUNITY, using the existing M0.1
Energy and P1 candidate projection. The caller supplies low/high path
distance, speed, extra WAIT time, and additional assumed Energy expense.
Missing bounds return UNKNOWN, never zero. G4 speed above the M0.1 source
cap is also UNKNOWN.

This is arrival-only arithmetic: seeing or reaching food does NOT
create EAT or Energy credit. Low/high scenarios assume complete input
bounds and a monotone unobstructed route. Nothing here reads World,
changes ledger, decides an action, or proves future success.

Comparison receives the existing sensor-derived Energy range, never
the true M0.1 host Energy, and returns only conditional affordability.
At 0.5 block/tick, 5-block travel costs 2.5 M0.1 units including
basal, compared with 1.5 for a movement-only cheap baseline.
10-block travel costs 5.0; low sensed Energy can separate which
candidate journeys are affordable, without choosing one.
A 4-6 block uncertain route, 0.4-0.8 block/tick, 0-3 extra WAIT
ticks and 0-0.5 extra assumed Energy produces an estimated 1.7-4.1
range. Sensor noise and unbounded hazards remain ambiguous or UNKNOWN.

Only offline engineering characterization has been done.
The route model is not integrated into the S49 issuer or live SelfBody,
and is not a replacement for Minecraft M0.2 exhaustion or verified
World outcomes.

## Actual SelfBody type compatibility and L1/L2 read-only handoff

M's new `experiments/metabolism_selfbody_cognition.py` is a
*separate, opt-in contract*, not a mutation of the product SelfBody.
Its only output, `CognitiveResourceContext`, contains original
session/self/epoch/native-seq lineage, optional owner WorldTick,
per-external-candidate **model** affordability labels, and
`action_authority=False`, `learning_updates=0`,
`habit_grants=0`. It never selects a candidate and does not
modify S49, S42, L1 retention, M0.1 or P1 states.

**Critical model mismatch:** existing product #634 has
`body.sensed("m0_energy_sensor")`, an owner-local
**B0 `metabolism_viability`** reading. That is not a
calibrated M0.1 `M01Profile` Energy observation. Therefore,
existing B0 views return `UNBOUND / UNKNOWN` for every M0.1
route (even when the B0 reading is high), not conditional
`MODEL_AFFORDABLE`. Native `food`/HP and B0 sensor are
never converted to virtual M0.1 Energy.

The future M0.1 owner may read its existing `M01State` and export
`M01OwnerSensorHandoff` **without true Energy** via
`export_m01_owner_sensor`. This local source includes a full-profile
SHA256, quantized reading, owner tick, native seq/request and two
structurally bound source references. The SelfBody owner must *separately*
authorize the actual World source and place a `BodyInteroception`
with **distinct new key `m01_energy_sensor`**,
`owner_provenance.source="m01-owner-local-sensor"` and the
matching M0.1 local reference. M's `from_selfbody_to_cognition`
then verifies the full source/session/epoch/owner tick,
profile hash, field origin, reading and native/owner provenance
before applying the existing sensor/route comparisons. Structural
matching cannot independently attest source authenticity.

**CI product-compatibility test:** M's own GitHub Action checks
out product SelfBody #634's exact
`087fe095a87594505392262da1d341cf0c65b2b2` in a **separate
read-only directory**, runs the *actual* product
`BodyObservation`, `BodyInteroception` and
`compose_self_body_view` types against the new M adapter,
and exercises both positive matching M0.1 (hypothetical producer)
and refusal of current B0-only product views. This requires
`python -m pytest -q -o pythonpath=product_selfbody_contract/src
tests/test_metabolism_selfbody_product_contract.py` with
`PYTHONPATH=product_selfbody_contract/src:product_selfbody_contract:src:.`
because this branch's ordinary pytest settings prioritize its own
`src` package. The original product source is unchanged.

The latest L8 lane only reads the already-returned S42 choice
after S epoch completion and keeps the S choice authoritative.
L8 does *not* consume M resource labels today. Future L1/L2
adoption is an **S/L-owned integration**. Until the original
M0.1 owner and independent S source admission are live,
this is a passing **offline, source-shaped contract**, not a
physical Body/Cognition activation or survival change.

## B0 actual owner → existing SelfBody / cognition bridge (2026-10-30)

The M-owned `experiments/metabolism_b0_cognition.py` is a separate,
read-only *one-owner-tick* interpretation of the **existing S #634 B0**
`B0EnergyLedger` / `B0Decision` / `compose_b0_cognition_views` seam.
This **does not** apply M0.1 distance pricing to B0. The B0 M0
`MetabolismConfig` units are per tick: WAIT costs `basal_cost` and
MOVE costs `basal_cost + move_cost`. Neither is Minecraft hunger,
M0.2 native exhaustion, joules, route distance, S49 action
authorization or a future food credit. EAT is not forecast; an
original S51 owner-confirmed consumption receipt remains necessary.

`read_b0_resource_context(views, owner_decision, config, sensor,
noise_bound=...)` requires the pre-existing joined SelfWorld/SelfBody
view and **the separate original B0Decision sensor reading**.
The sensor must be an interoception named `m0_energy_sensor`, bound
to exactly the same native probe/session/request/owner tick and owner
source `b0-m0-owner-local-sensor`; decision source seq, tick, kind
and reading are checked independently of the SelfBody field. A
sensor-only mutation with otherwise valid-looking references now
fails rather than being treated as a real changed bodily state.

Under an *explicit assumed* deterministic B0 gain/bias/quantization
and bounded noise, the module calculates an outward-rounded sensor
interval and emits `MODEL_AFFORDABLE`, `MODEL_INSUFFICIENT`,
`MODEL_AMBIGUOUS` or `UNKNOWN` per WAIT/MOVE proposal. No
noise bound, zero-gain sensor or impossible sensor reading => UNKNOWN.
No preference/Action/habit/reward/true Energy is produced.

The actual product test imports S #634 exact immutable HEAD
`087fe095a87594505392262da1d341cf0c65b2b2` into a **separate
read-only checkout** in M branch CI. Because the M branch base has
older adapter modules and the product branch lacks M0.1 modules,
the CI explicitly loads S's `python_protocol` and
`relay_self.self_body` from the product checkout and extends
the experiment package path *only* for M additions. This is
test-time isolation, not a source modification or partial merge.

**Focused offline contrast** using actual product B0
`B0EnergyLedger.decide` and `compose_b0_cognition_views` with
synthetic Mineflayer probes: B0 basal 0.5 and move extra 0.25;
sensed E=12 => both WAIT/MOVE model-affordable; E=0.6 =>
WAIT model-affordable, MOVE model-insufficient. Blind zero-gain
sensing gives the same observed reading and UNKNOWN for both,
demonstrating that true host Energy is not secretly consulted.
Re-reading makes no ledger/food/Action changes. Negative tests
reject altered decision reading, sensor-only alteration, owner
tick, native/owner provenance, identity, and source scope.

**Qualification and model limits:** the calibration and
`MetabolismConfig` are still caller-supplied; this bridge cannot
authenticate their identity or a genuine original World sample.
The contract test explicitly shows that passing a wrong movement
cost changes a *model-only* result, and does not hide that limitation.
B0's existing L0 choice is retained; no S49 action, M0.1 owner
activation, L8 decision modification or physical World experiment
is claimed. A cheap B0 exact one-tick cost rule is already sufficient
for this output: no unique cognition/learning advantage is claimed.

## Original S42 epoch result ↔ B0 resource readout (2026-10-30)

M's `experiments/metabolism_s_epoch_resource.py` is a **post-decision**
observer. The S owner must already have run the original
`coordinate_decision_epoch` (or `coordinate_planned_epoch` with
real nonempty executed work IDs). A typed returned
`WorldConditionedChoice` is accepted **only if cognition completed,
no Action timeout was emitted and no Action deadline remains open**.
It is checked against the independently supplied original
`NativeThreat` and `LearningPreferenceState` by replaying the
**existing pure S42 `select_world_conditioned_choice`**. No S runtime
coordinator, model, supervisor, native sensor or Action is invoked by
the M post-epoch observer itself.

The original S choice's session/native seq/request/provenance must
match the previous B0 owner/Body/World resource context's same probe.
The original S choice **always wins**, even if the B0 toy model
labels a single WAIT or MOVE tick energy-insufficient.
The result merely records `MODELED_TENSION`, including unknown/
ambiguous cases. No agent goal, new reward, hardcoded hunger
preference, L0 rule, L1 habit or Action authorization is minted.

The latest pinned product S #634 original API test executes all of
`B0EnergyLedger.decide`, `compose_b0_cognition_views`,
`coordinate_decision_epoch`, and S42's original
`select_world_conditioned_choice` on the **same synthetic native
probe** before calling the M adapter. In the close-zombie condition
S42 picks `MOVE_AWAY` at both B0 sensed E=12 and E=0.6,
while B0's hypothetical one-tick MOVE costs 0.75 and is
model-insufficient at E=0.6. Far-zombie S42 picks WAIT;
at E=0.4 even WAIT may be model-insufficient due to basal 0.5.
Blind/noisy sensor yields UNKNOWN/ambiguous, never forced Action.

**Critical units warning:** S42's `MOVE_AWAY` is a World-conditioned
choice, not itself an executed full S49 backward locomotion receipt.
B0's **per-simulated-step generic MOVE** is only an indicative
counterfactual, NOT a certified cost of an S49 MOVE_BACKWARD
trajectory or actual survival. The M0.1 distance/P1 route model
remains separate, and the real G4.13 physical gait receipt
UNKNOWN scope is not widened. The B0 owner profile/calibration
is still caller-supplied; no independent original native admission
or owner identity proof arises from typed dataclasses.

All integration remains M-owned experimental code on the isolated
M branch. No adoption of the hook into product S #634,
L8, S49, #545 or main; no fresh World, GPU, FULL,
qualification or SCIENCE is run. S/L owners can opt in only
after independently validating the original native source and
coherent B0 model profile.
