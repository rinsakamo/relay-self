# V3 / #619 — prospective M0 net-energy endpoint, not V2 retroactive reinterpretation

**Authority:** #619 V, #544 scientific gates, #537 S product, #575 R. One existing V Draft #625; no additional issues or PRs.
**Source of new design:** V2 exact immutable head `920d5742692d920987d1c321138893cb63c3de8d` established that the old V2 primary terminal-free ticks is **necessarily 16/16 in every valid arm** under E12, 16 ticks × basal0.5 and maximum 8 MOVE × extra0.25. It is intentionally **not** silently altered: `v2_knockdown_manifest.json` and prior evidence are frozen.

## V3 new *prospective* primary

**M0 end energy at global decision-tick 16**, a strictly experimental body ledger, conditional on completed/source-admitted episode with all 16 expenses and at most one independently verified EAT credit:

`E16 = 12 − 16×0.5 − 0.25×issued_MOVE_count + 4×independently_qualified_EAT_count`

This outcome **can distinguish** a simple policy's verified food/effort allocation while old V2 terminal-survival cannot. It does **not** by itself establish real Minecraft physical fitness, learned valuation or irreplaceable cognition. S #545 already produces source-shaped E/meal/MOVE fields in opt-in `groundv2`; this is a source-level *candidate*, not a live trial.

**Four arms remain identical:** SENSOR_ON, SHAM_ON, SENSOR_MASKED (gain0 + bias12, not neutral ablation), CHEAP_NATIVE (`native_only`). Fixed horizon 16, total MOVE max8, one operator-staged ground item at M0 tick11, source-matched initial World/sensor/food/budget. At least four independent World starts × all four arms is an **engineering feasibility floor**, not statistical power or confirmatory significance. Each start must be reset/attested; World-native time and exogenous food opportunity timing must be independently R-qualified and comparable across all arms. An M0 tick is **not** elapsed Minecraft World time. Native before/after `snapshot.time` bracket is only a bracket, not command-ack or interarm sync.

**Contrasts, always report individually, never aggregate away the cheap null:**
- ON minus sham: detects toggle/transport/infrastructure confound and sampling variation.
- ON minus masked: bounded effect of *this hand-coded sensor-gated policy*, not evolved sensor necessity.
- ON minus cheap: primary incremental complexity/value check; **if equal or worse versus cheap**, report `CHEAP_EQUAL_OR_BETTER` and **no incremental sensor benefit**, even if masked has worse output.

Measure original S50 MOVE outcomes, S51 EAT source/credit, M0 tick count, final true ledger, original native World snapshots incl. Food and native time, wall/CPU/GPU latency and cost separately. No credit for pickup metadata alone. Memory/L1/L2 learning, selection, value, habit and transferred cognition **not tested**.

**Interpretive gates:** Real World/EAT/clock original bytes independently R/V admitted first; operator staged food and lack of native collect-event must stay explicit. Randomized/paired World start and fixed temporal opportunities before real data. Four starts alone do not support inferential science; even an observed strong ON-vs-mask result yields at most bounded designed-policy dependence unless stronger cheap controls are beaten on real independently held-out conditions. World branch divergence after treatment is expected. No repeated-run fallback or posthoc threshold/primary changes.

## Implemented scope and non-go

- Immutable versioned `v3_m0_energy_manifest.json` alongside frozen V2 manifest.
- Pure validator `v3_m0_energy.py` checks all four arms, independent seed/start, identical reset digest within pair, nonissued WAIT semantics, complete ticks/MOVE/EAT limit and exact M0 accounting. It **only accepts synthetic source-shaped records**; SHA strings are not proof of originals.
- Negative tests and synthetic cheap-equivalence witness in `tests/test_validation_v3_m0_energy.py`. V CI pins latest S source independently and checks its M0 constants, arm map and new opt-in global mode source tests. No physical call.

**Current:** `V3_NEW_PROSPECTIVE_PRIMARY_NOT_RUN / G3_NO_GO / NO_PRODUCTION_GO`. No operator World authorization, Java/Node/GPU or LLM POST, nor actual four-arm World comparison. This is preparation, **not** a promotion of V2 historical results.


## V3 G0 policy-discrimination ceiling: ON vs CHEAP (pre-run source audit)

V3 fixed the V2 survival-time primary, but this *particular* single-item
study still contains a deterministic **mechanism-equivalence** null.
The only first ground food opportunity is at **M0 decision tick 11**;
all four arms must have made 11 basal WAIT steps without earlier food.
With true E0=12 and basal cost0.5, E11=6.5. The unchanged
`Interoception(gain=1,bias=0,quantum=1)` quantizes 6.5 via
Python ties-to-even `round` to **6**, below the hand-coded
`sensor_gate` SEEK threshold of **8**. On the same native hungry
single-item probe:

| Arm | Readout | Designed L0 choice |
| --- | ---: | --- |
| SENSOR_ON | 6 | SEEK |
| SHAM_ON | 6 | SEEK |
| SENSOR_MASKED | 12 (fixed high) | WAIT |
| CHEAP_NATIVE | reading irrelevant | SEEK |

Thus ON and the **strong cheap comparator take the same first
food-seeking decision by construction**, while ON and MASKED differ.
If later World observations, initial sources, action success and
decision-tick updates remain identical, ON and cheap have the
same subsequent controller trajectory on this one-item protocol:
the sensor-gate condition has no chance to reject a food opportunity
that the native-only baseline accepts. This *conditional* policy
equivalence is **not** attestation that different live Minecraft
runs have identical trajectories; async movement, server timing and
source variability remain unknown until R/V inspection.

New `review_fixed_fixture_first_choice()` conservatively reports
`V3_FIRST_OPPORTUNITY_ON_CHEAP_POLICY_EQUIVALENCE`, NOT a positive
sensor-value claim. V CI independently imports pinned real S
`B0EnergyLedger` with the native-shaped one-item fixture, charges
exactly eleven M0 WAITs, and checks actual L0 outputs for all four
arms. The positive ON-vs-MASKED difference is therefore an engineered
policy contrast, **not** evidence of added value versus cheap.
The versioned V3 end-energy primary is mathematically variable, but
this *particular* fixture is not a good test of sensor superiority
over a cheap fixed policy. No V2/V3 frozen manifest update, no
actual trial, and no change in scientific G3 NO_GO.

For a future valid comparison, V would need a **separately versioned
prospective scenario where the sensor-gated policy can both accept and
decline opportunities**, and where accepting a low-value opportunity
has a measurable energy/opportunity cost for the cheap baseline.
That design must also avoid building the desired superiority into
the handcrafted threshold/fixture schedule. No new study/World
permission is implicitly granted; R's independent on-host
original audit continues separately.
