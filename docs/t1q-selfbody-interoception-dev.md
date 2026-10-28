# T1q — original SelfBody v0 × T1p normal Runtime interoception (DEV candidate)

Baseline T1p: `56dd88698dbff7f1ed3a40c8c33aaa12c8067d0b`.
Source SelfBody: Draft PR #634, `087fe095a87594505392262da1d341cf0c65b2b2`,
exact read-only source blob `src/relay_self/self_body.py` SHA
`36cd5ab76b1e1f427741b6dc128407b790784e6f`.

**DEV_ONLY / OFFLINE_IMPL_ADDED / T1Q_NATIVE_UNVERIFIED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Intended narrow integration

T1p already proved that the original single-owner Paper → S51/S49 →
clear → T2/M0/P1 bounded two-MOVE DEV loop runs in Minecraft. It left
true M0 energy and P1 fatigue inside the host safety evaluator, with no
Self-side interoception. T1q adds that *information edge* only.

- Reuse exact **existing** #634 `SelfBodyView`, `BodyObservation`,
  `BodyInteroception` and `compose_self_body_view` via one copied,
  unmodified source blob. This is a staging copy, not a new persistent
  owner or adoption into #634. Do not merge either branch blindly.
- Use existing `MineflayerPaperSnapshot` already `ADMITTED` and consumed by
  original T1e single session reader and `TickAccounting`. Snapshot
  `session_id`, native `seq`, Paper `world_tick`, source index and exact
  owner ticks are checked. This is a **Paper/T1f-specific DEV projection**,
  not #634's ordinary `MinecraftPresent` projection and not independent
  physical source authentication.
- `BodyObservation` receives only native observed position/health/food,
  with `BodyOrigin.OBSERVATION`. B0's existing `observe_energy` and
  P1's existing `observe` produce `m0_energy_sensor` and
  `p1_fatigue_sensor` with `BodyOrigin.INTEROCEPTION`, separate owner
  clock/provenance, and finite quantized values. True energy/fatigue
  never enter the cognition summary; default experimental sensor quanta
  for this DEV adapter are 0.25 Energy units and 0.01 fatigue units.
  They are engineering choices, not calibrated physiology.
- Paper World `getFullTime`, Node seq, and M0 ledger ticks are distinct.
  P1 physical fatigue state follows source WorldTick, but **WAIT_DEV is not
  P1-qualified full-tick WAIT**. Producing a sensor is not a fatigue
  recovery or Motor authorization.
- T1p's single `run_body_loop_dev` accepts one optional cognition
  decision callback. Legacy T1p defaults unchanged; T1q callback reads
  SelfBody, uses sensed energy <=3 to HALT and sensed fatigue >=0.05 to
  HOLD_BODY. These are a **designed bounded L0 heuristic**, not learned
  cognition or a validated fatigue-driven advantage.
- T1p's original exact host safety guard remains first and wins. A sensed
  reading can only restrict MOVE. Sensor UNKNOWN cannot grant movement.
  Only original S51 issuer/S49 executor/S16 clear, native re-admission
  and unique Action/Effect remain physical authority.
- The original T1e post-shutdown audit still verifies exactly two native
  set_control/clear effects, unique IDs, source continuity, original
  M0/P1 accounting, exit0 and cleanup. T1q separately checks sensor
  decision/native seq/WorldTick correspondence. No new native reader,
  new World source, LLM/GPU, Paper command, new M0/P1 model, or TPS actuator.
- Ordinary Node synchronous timing trace stays OFF. The original
  `native.jsonl` remains the canonical source.

## Verification required on LocalCodex physical machine

First verify remote branch/HEAD, clean worktree and the exact source #634
blob. If physical code HEAD differs from the branch, reconcile first.
Use Python 3.12 and the existing dependency environment:

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_t1q_interoception_dev.py \
  tests/test_t1p_body_runtime_dev.py \
  tests/test_t1f_t2_dev.py \
  tests/test_self_body.py
# If test_self_body.py is absent on this staging branch, do not pretend it ran.
# Run closest existing typed-view tests and source-contract tests instead.
# Then focused Python 3.12 FAST/Ruff/contracts; no unneeded FULL.
```

Then run exactly one new isolated, disposable Paper1.21.8 World under the
original T1e launcher after focused/FAST PASS:

```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.t1e_native_dev \
 --cases t1q_body_loop --loop-moves 2 --node-trace off \
 --output /NEW/ABSOLUTE/T1Q-001 \
 --paper /EXISTING/VERIFIED/PAPER.jar \
 --plugin /EXISTING/VERIFIED/PLUGIN.jar \
 --bootstrap /EXISTING/READONLY/BOOTSTRAP \
 --confirm T1E-DISPOSABLE-DEV-ONLY
```

Check both per-epoch SelfBody `native_seq/world_tick` against the
native Action source in the **same** World, that only
`INTEROCEPTION` carries M0/P1 sensor readings and health/food
are `OBSERVATION`. Check the sensor values are truly quantized,
not exact ledger state. Require positive native motion, OUTCOME2/clear2,
consecutive World accounting, legitimate WAIT_DEV and M0 BASAL,
trace OFF, no extra commands and complete cleanup.

Do **not** force a real high-fatigue or low-energy intervention just to
show behavior change. Offline controls must show different sensory values
can cause HALT/HOLD while an unchanged exact host guard still owns physical
permission. A real T1Q-001 healthy run may reasonably choose MOVE twice;
that is not evidence of adaptive benefit or a real behavioral counterfactual.

Preserve all failed trials and tests. Report exact code-head, original World
and logs, SHA256, observed values, source identity, negative controls,
cleanup; fix and rerun as fresh World IDs if needed. Publish result under
existing #537/#627/#632 and #616, but do not amend #634 or #626,
main or protected history. `DEV_WORLD_OBSERVED` **only after actual
new Minecraft run**; R/SCIENCE remain NO_GO/NOT_RUN.
