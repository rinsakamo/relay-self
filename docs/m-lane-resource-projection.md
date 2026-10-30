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
