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
