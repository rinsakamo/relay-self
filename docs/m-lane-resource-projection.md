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

## M × L8: independent same-S-epoch learning/resource shadow (2026-10-30)

The M-owned optional `experiments/metabolism_l8_resource_shadow.py`
joins **already returned, same-object** `DecisionEpochResult` instances
from the **actual L8 `observe_s_epoch_l1`** and the existing M
`observe_completed_s_resource_epoch`. The original L8 pure
`observe_s_epoch_l1` verification is rerun against the supplied
`NativeThreat`, frozen S10 preference, L1 `LearningEpochResult`
and explicit retention flag. The existing M *pure* S42/source/model
post-epoch verification is likewise rerun. Neither S coordinator,
model call, Memory owner, ledger nor Action issuer is rerun by the
joint bridge. The S choice remains unchanged.

The handoff exposes the three **distinct** pieces of information:
(1) original S42 WAIT/MOVE_AWAY, (2) the L8-admitted
experience/cheap-rule shadow candidate, or no admissible candidate,
and (3) the *generic B0 one-tick* modeled affordability of that
candidate alongside any S-side model tension. It does **not**
select a winner, rank a combined utility, award new reward, perform
an L1 update, grant an S11 habit, or generate an Action. L8's
`CHEAP_DIFFERS` must remain labeled as a cheap-rule comparator,
**not** an experience learning success. The synthetic model output
does not establish why an organism prefers either option.

**Source clock distinction:** L8's `ShadowContext.source_revision`
is a caller-assigned observation revision, while B0
`B0CognitiveResourceView.owner_tick` is the simulated metabolism
owner clock. These values must **not** be made equal. The join
instead requires the **exact same original S epoch object**, matching
native probe/session/request, L8 evidence SHA membership, same
S42 choice, source scope, immutable planned work IDs, and the B0
owner tick's own **owner-specific** source reference. It rejects
forged or future/in-flight S Action, altered S choice, unadmitted
L1 candidate, changed L8 digest, changed retained preference,
mismatched S/L8/M epoch or altered M modeled tension.

**Pinned offline tests, deliberately separated by owner:**
- Original S #634 `087fe095a87594505392262da1d341cf0c65b2b2`
  is independently checked out read-only and tested with its actual
  B0 owner/Body and S42 coordinator. This original producer suite
  does **not** run real L8.
- Original L8 `4defb6e8b78f2e050921b521eb2253a14bc260c4`
  is independently checked out read-only and tested with its actual
  L6/L7/L8 original fixture, S coordinator and L8 observer; in
  these combined cross-branch cases the B0-cost readout is **synthetic
  and source-shaped**, not a genuine B0 owner handoff. This checks
  the immutable join semantics, not a simultaneous S+L+M product
  activation.
- Case examples: near threat S=MOVE_AWAY, L8=WAIT; low modeled
  B0 Energy makes S's generic MOVE cost insufficient but L8's
  WAIT model-affordable; high Energy changes only M. Far threat
  S=WAIT, L8=MOVE_AWAY with low Energy: L8 candidate generic MOVE
  model-insufficient; S remains WAIT. L8 retention-OFF has no L1
  proposal, even when M labels a cost. Cheap equivalent remains
  `CHEAP_DIFFERS`. Corrupt lineage/digest/deadlines/model refs fail.

The B0 MOVE estimate is **not** a cost attestation for physical
S49 MOVE_BACKWARD or the G4 planned gait, and B0 Energy
is **not** M0.1 virtual Energy nor Minecraft native M0.2 exhaustion.
No physical World, EAT-credit, output utility, L8/Body/product
branch mutation, model/GPU execution, actual L1 behavior change,
QUALIFICATION or SCIENCE has been performed.

## Same-process S #634 B0 producer + L8 observer + M adapter (2026-10-30)

We now test the three components in **one Python 3.12 interpreter**
against the **same single original-shaped `MineflayerObservation`**
from L8's retained learning fixture, not three separately constructed
source pointers.

`tests/test_metabolism_same_process_slm_product.py` and the appended
M-only CI job load the **exact pinned original S #634** checkout
`087fe095a87594505392262da1d341cf0c65b2b2`
and **exact pinned original L8** checkout
`4defb6e8b78f2e050921b521eb2253a14bc260c4`
side by side, with S's physical-layer models and Python protocol,
and L8's missing learning modules. They assert source module provenance
during import rather than silently swapping a different implementation.

For each synthetic native probe, the actual S producer
`B0EnergyLedger.decide(probe)` computes its M0 interoception;
`compose_b0_cognition_views(probe, ledger, decision)` maps that
**actual original owner sensor** into joined SelfBody/SelfWorld; the
M `read_b0_resource_context` matches this owner decision and
the exact same native seq/request/provenance. The actual original S
`coordinate_decision_epoch` returns its unchanged S42
`WorldConditionedChoice`; L8's actual `observe_s_epoch_l1`
accepts a previously prepared L6 training/context snapshot; M's
`observe_completed_s_resource_epoch` and
`contrast_l8_with_m_resource` join both results **without
rerunning the S coordinator** or writing to the owner.

**New distinction from previous test:** L8's B0 resource hint in
this one-process job is *not manually fabricated*; it is produced
by the **real pinned S B0 owner and SelfBody product code** and
read from the original decision's sensor. The input probe and
prior L6 experience are still synthetic fixtures and the two
original product branches are layered in the CI interpreter:
this is an **experimental composition**, not a deployed product
or original Minecraft native-byte attestation.

Tests cover low/high B0 modeled energy (S=MOVE_AWAY,
L8=WAIT regardless of M), distant S=WAIT with L8=MOVE_AWAY
model-insufficient, retention-OFF/no candidate, cheap-memory-rule
counterexample, blind zero-gain sensor with UNKNOWN, no mutation
of B0 owner or S Action supervisor, and negative controls for
altered B0 original decision, wrong session/epoch, counterfeit
owner source or L8 proposal. No new physical Action, independent
model call, P1/gait receipt, food credit, new learning update,
Habit promotion or real World survival evidence is asserted.

**No new runtime admission:** S owner source is **synthetic**
despite the original production Python API. B0 M0 1-tick
costs are not physical S49 MOVE_BACKWARD or G4 gait
costs and cannot be substituted for M0.1 modeled distance
Energy or native Minecraft exhaustion. Actual one-command
S/L/M runtime opt-in and real Minecraft DEV still require a
separate owner-controlled integration step; do not merge the
independently owned product branches simply because the
experimental interpreter can import them.

## One-call post-S-epoch opt-in seam (2026-10-31)

`experiments/metabolism_s_l_m_post_epoch.py` provides
`read_s_l_m_after_owner_epoch(...)`, a **M-owned library function**
for an *original S owner* to invoke **after its existing B0 L0 decision
and S42 decision-epoch coordinator have returned**. It does not
install itself in S's real Minecraft host loop and does not run
the original S coordinator or L0 again. It is an adoption seam,
not a deployed S49 product integration.

An owner already holding these **original live objects** may supply:

- `probe`: the already read `MineflayerObservation`;
  `native`: the already derived `NativeThreat` whose
  `native.observation is probe` (identity, not a new decoding);
- `ledger`: original `B0EnergyLedger` from that session;
  `original_b0_decision`: its already returned `B0Decision`;
- `original_s_epoch`: returned original S
  `DecisionEpochResult` or finished `PlannedDecisionEpochResult`,
  with source/retained S42 check and no timeout/open Action deadline;
  and `retained`: exactly the S10 snapshot used for that choice;
- `self_id`, `epoch_id`: source-owner caller identity;
  `learning` and explicit `retention_enabled` together
  (opt-in only), if an **already computed, properly admitted L8
  `LearningEpochResult`** is available.

The adapter composes existing S product SelfBody/World with **the
original B0 sensor**; reads one-tick model cost from that same
ledger's **original config/sensor**; validates the original B0
decision/reading/probe/tick, then computes the existing S/M
post-epoch contrast. Only if L8 inputs are explicitly present does
it run the original **pure L8 observer** and immutable M/L8
comparison. Without L8 inputs, it returns an M-only readout,
never a synthetic no-memory recommendation.

**Fail-closed:** copied but equal probe with a different object,
stale owner decision, ledger advanced between decision and
passive read, foreign session/probe/retained S10, missing L8
admission, S Action timeout/in-flight, and counterfeit B0 source
are rejected. Default `noise_bound=None` gives an UNKNOWN
energy interval: the owner must explicitly supply a real bound
before claiming model affordability; `noise_bound=0` is only
appropriate for a controlled deterministic model fixture.
`source_attested=False` is fixed. Readout explicitly reports
zero new native reads, cognition calls, action issues, M food
credits, learning updates and habit grants.

**Owner call placement in a future DEV host:**

```python
# Original S driver (not inserted by M code):
# probe = <the one already obtained native probe>
# decision = existing_b0_owner.decide(probe)
# s_epoch = existing_s_owner.coordinate_existing_epoch(...)
# retained, native, l8_snapshot are original owner-approved inputs.
from experiments.metabolism_s_l_m_post_epoch import read_s_l_m_after_owner_epoch

shadow = read_s_l_m_after_owner_epoch(
    probe=probe, native=native, ledger=existing_b0_owner,
    original_b0_decision=decision, original_s_epoch=s_epoch,
    retained=retained, self_id=self_id, epoch_id=epoch_id,
    learning=l8_snapshot, retention_enabled=True,
    noise_bound=None,  # remain UNKNOWN absent explicit calibration
)
# shadow is observational; never pass it to S49 as authorization.
```

This illustrative call is *not* a claim that any existing product
host already has all those inputs or runs L8. The function requires
a source-qualified S42 zombie threat and finished S decision;
other World observations must be skipped, not coerced.
The qualified L8 experience source / Goal labels and physical
S49 action receipts must still be obtained independently by
the responsible owners. None are manufactured by M.

**Physical DEV remaining:** Install an explicit opt-in passive
hook in an S owner-controlled host without changing the existing
S49 issuer, use the original live Mineflayer probe and genuine
owner-owned L8 snapshot, run in a disposable Minecraft DEV World,
and record the unchanged Action issuer plus downstream outcome
with native source correlation. No host modification, World run,
physical Action, L1 policy change or scientific survival benefit
is evidenced by this library-only milestone.

## Fault-contained opt-in DEV host diagnostics (2026-10-31)

`experiments/metabolism_slm_dev_host_tap.py` provides
`observe_optional_s_l_m_dev(enabled=False, original_s_epoch=..., **originals)`
and `bounded_s_l_m_audit_row(result)`.

**Purpose:** before an S owner opts into passive M/L8 telemetry,
it must be possible to let the exact original S action-control
path proceed even if the *optional observer itself* rejects a source
or has a software exception. This is **not installed** into the S
product host; it is a typed M-owned, off-by-default integration
component for an S owner to call **after** its already finished S
decision epoch. No new S49 action issuer is installed.

Behavior, in order:

1. When disabled (default), never import original S/L8 B0 product
   modules, inspect a native probe, or call any optional observer.
   Non-boolean `enabled` is treated as invalid/disabled, never
   a truthy permission.
2. When explicitly `enabled=True`, consume the caller's *already
   returned original S epoch object* plus original B0 decision/probe
   and optional precomputed L8 snapshot. Run the existing source-bound
   `read_s_l_m_after_owner_epoch` only; do not call S coordination,
   B0 `decide`, L8 `advance_learning_epoch`, S49 issuer or any
   World/LLM provider. For a genuinely planned S result, the inner
   original `decision` object is used for source binding, while
   the outer original `PlannedDecisionEpochResult` identity is
   returned unchanged.
3. Valid admission produces `RECORDED`; original source mismatch
   or in-flight/unknown S boundary produces `DEFERRED`; an ordinary
   unexpected observer exception produces `OBSERVER_ERROR` with a
   **fixed reason code, not leaked exception or native data**.
   Interruption exceptions (`KeyboardInterrupt`, `SystemExit`)
   are not masked.
4. `bounded_s_l_m_audit_row` emits an allowlisted JSON-safe
   diagnostic record: session/probe/request references, original
   S choice, L8 candidate/comparison status, M model tension,
   and L1 generic resource-model status, or the skip/defer code.
   It excludes the **original object**, raw Minecraft frames,
   true M0 Energy, health, native inventories, L8 Memory contents,
   and actual S Action outcomes. It rejects invalid/truncated
   source reference strings, mismatched audit status/reason,
   bogus L8 candidate/scope/model tension or injected authority.
   Fields `source_attested`, `action_authority`,
   `new_native_reads`, `new_cognition_calls`,
   `action_issues`, `learning_updates`,
   `habit_grants`, `food_credits` are all pinned false/zero.

**Owner integration example (illustrative only; no product hook yet):**

```python
# Original S host owns these existing objects; no re-reading World.
# s_epoch = <already returned original DecisionEpochResult>
from experiments.metabolism_slm_dev_host_tap import (
    observe_optional_s_l_m_dev,
    bounded_s_l_m_audit_row,
)

tap = observe_optional_s_l_m_dev(
    enabled=dev_observer_opt_in,
    original_s_epoch=s_epoch,
    probe=existing_probe, native=existing_native,
    ledger=existing_b0_ledger,
    original_b0_decision=existing_b0_decision,
    retained=existing_s10_snapshot,
    self_id=self_id, epoch_id=epoch_id,
    learning=previously_admitted_l8_result,
    retention_enabled=True,
    noise_bound=None,
)
audit = bounded_s_l_m_audit_row(tap)
assert tap.original_s_epoch is s_epoch
# S49 uses only S's original admission, not audit.
```

Do not interpret a `RECORDED` row as authenticated real
Minecraft origin: native source trust is explicitly *false*.
Likewise `OBSERVER_ERROR` being contained does **not** prove
physical runtime delivery or a liveness guarantee: actual S host
integration and its real World operation remain to be exercised
by the S owner. In CI, original fixed S #634 and L8 are loaded
read-only in one interpreter with synthetic source-shaped probes.
No new provider, Java, Node, GPU, World, physical Action or
QUALIFICATION/SCIENCE execution.

## S49 original live_probe source callback → M/L8 post-epoch lease (2026-10-31)

**Exact actual S49 insertion location found:** pinned original
`adapters/mineflayer/s49_normal_session_real_ci.py` exposes
`qualify(..., live_probe: async Callable | None = None)`. Its
`reprobe(frame)` obtains the **original** `_correlated_observe`
typed native probe, then `await live_probe(reading)`, then passes
that same probe object back to `NormalWorldL0.run_session`.
This is **before S49 L0 selection/Action issuance**; it is NOT an
already completed S42 `DecisionEpochResult`. S49 remains the
one actual Action authority. The ordinary S49 runtime does not
currently own a complete B0/M + L8 + S42 same-epoch bundle
or install this M post-S observer.

The new M-only `experiments/metabolism_s49_live_probe_bridge.py`
provides `S49PassiveSourceLease(enabled=False, max_probes=4)`.
`lease.observe` is an async method with **no await inside**,
compatible with the original S49 `live_probe` callback. No
additional native read, model, B0`decide`, Action, I/O,
filesystem, task or scheduling is triggered by this callback.
It stores *at most one already received original typed native
probe object*, by identity (memory-only, no persistence).
The bounded `S49PassiveSourceSummary` reports no authority,
physical source attestation, learning write, energy credit
or Action issuance.

An S owner MAY optionally call
`lease.observe_after_original_s_epoch(...)` **only after** it
separately has the original source-qualified, finished S42
decision, original B0 owner decision and ledger, and
source-admitted L8 snapshot. The lease checks that the
`NativeThreat.observation` **is that exact captured probe**
and immediately consumes the one-slot source pointer, before
calling the already-tested, disabled-by-default M passive
diagnostic function. Reusing the same lease without a new
probe fails closed; a later native probe invalidates the older
one. Incorrect native provenance, source replay, foreign
session, wrong phase or capacity overrun clear the lease
without interrupting S49.

**Original S49 integration-site contract, not installed product code:**

```python
from experiments.metabolism_s49_live_probe_bridge import S49PassiveSourceLease
lease = S49PassiveSourceLease(enabled=True, max_probes=3)
# Existing S49 operator would pass:
# await s49.qualify(report_path, server_log, live_probe=lease.observe)
# ... that original callback runs strictly *before* S49's L0 choice.
# Once a future S owner independently supplies a finished S42 result,
# a B0 owner decision/ledger and an admitted L8 snapshot:
audit = lease.observe_after_original_s_epoch(
    original_s_epoch=s_epoch, native=native, retained=retained,
    ledger=original_b0_ledger,
    original_b0_decision=original_b0_decision,
    self_id=self_id, epoch_id=epoch_id,
    learning=l8_snapshot, retention_enabled=True,
    noise_bound=None,
)
# audit is not a S49 Action or an S10/Habit commit authorization.
```

**Offline proof scope:** CI combines the exact pinned original
S #634 `NormalWorldL0.run_session` (not a copied simulator)
and `S49PassiveSourceLease.observe` on a single synthetic
correlated event/probe. It verifies the original S49 choice and
Action **request** remain independent of the passive source
pointer, then joins the already-created original S42/B0/L8
readouts on that exact same object. This does **not** call
S49's physical `NormalSessionActionExecutor.execute` nor
`s49.qualify` with Java/Node; it cannot be used as a claim
that real World data, an S49 Action OUTCOME, a persistent L8
learning update, an original live B0 owner, or a real runnable
S/L/M post-decision hook are already in the S49 host.

**Next required actual physical integration:** S owner must
opt in at its own original host boundary and provide an
actual S42/B0/L8 completed-epoch snapshot without creating
a second Action/World owner. The missing exact owner
handoff cannot be filled by synthesizing a second B0 ledger
or rerunning S42 during the callback. The S49 original
Action path, W4 protected originals, S #634, L8 and P1
remain untouched; new M code is only on isolated DEV branch.
