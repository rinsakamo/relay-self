# T1v — physical rest before Action != causal S49 WAIT (isolated DEV)

**DEV_ONLY / DEV_WORLD_OBSERVED / PHYSICAL_IDLE_VERIFIED /
NATIVE_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Two new disposable Worlds verified initial physical idle (one charged tick each).
Both runs FAIL at onset; continuous gait accounting remains unestablished.
The second run records 24 post-refusal diagnostic ticks through the existing
reader without resuming P1/M0 or issuing a second Action. See
[actual native results](t1v-native-dev-results-20261028.md).

Base exact T1u HEAD: `754602008010d6cd719a866d54be2df65c8d748a`.
T1u source report: [docs/t1u-native-dev-results-20261028.md](t1u-native-dev-results-20261028.md).

## Actual failure being addressed

T1U-001 had 0 Actions and refused at a physically quiet **pre-Action**
source tick because the provider required a S49 causal clear for its
only WAIT output. That conflated *physical body recovery while motionless*
with *S49 post-Action WAIT_DEV eligibility*. Source original endpoints
had to be distinguished without inventing a clear ACK.

The T1U-004 subsequent failure was on an Action's **start edge**,
where two stable applied back-control endpoints could not be proved.
T1v does NOT turn that unknown into a synthetic JOG or WAIT. It remains
an independently diagnosed, unresolved boundary.

## Minimal separate DEV witness

New `adapters/mineflayer/t1v_physical_idle_dev.py` reuses the
same existing Paper/Node callback, plus untouched T1u strict gait
provider. For a sampled physical-idle interval, independently require:

1. Same admitted, contiguous session / World / boot / player and
   challenge source lineage, one WorldTick between snapshots.
2. Equal sampled horizontal/vertical position **and** unchanged Paper
   cumulative physical-motion counter; Paper input 0 on both.
3. Both Node `applied_controls_dev` endpoints have all seven controls
   false, and both Paper `gait_dev` endpoints report no sneak,
   sprint or modifiers and baseline movement speed.
4. No sampled threats; original source says threat coverage complete.
5. Original control phase and generation stable, exactly `INITIAL`
   or `CLEARED`; no transition edge silently presented as rest.
   Causal challenge timestamps postdate both phase markers.

All other source intervals still pass to the **original unchanged
T1u provider**, which rejects unproven onset / residual / unsupported
gait. A caller-created `GaitTickDev(\"WAIT\")` alone does not
bypass these conditions; the existing T2 physical witness is checked
again independently.

The body may recover under the existing `advance_gait_dev(...,
GaitTickDev(..., \"WAIT\"))` while physically inactive, even before
there has been any S49 Action. This is DEV virtual-Body physiology.
It **must not** set the original action-level `WAIT_DEV`,
`wait_causal_clear` or R-qualified WAIT flags. The original
`activity` becomes `PHYSICAL_IDLE_DEV`, with explicit
`physical_idle_model_only=true`, `qualified_physical_wait=false`,
`gait_source_authenticated_R=false` only in opt-in gait rows.
M0 basal and L0 work cost still accrue once. Old P1 transition
and all legacy T1p/q/r/s row field sets stay intact by default.

This accepts only a sampled DEV body-rest hypothesis. Two endpoint
observations do **not** establish every nanosecond of the intervening
tick or an R/V full-World attestation. It is neither physiological
human validation nor permission to issue MOVE.

## Isolated new Minecraft case

`t1v_physical_idle_loop` uses the same T1e/Node/Paper callback,
same original S49/S51 single issuer, and default-off pre-existing
`t1u-gait-dev` instrument. It selects
`applied_gait_or_physical_idle_dev`, with the existing **unchanged**
four-gait P1 blob `d241978d0eba1843e3a6caed96c90e3c16e8dc39`.
No second P1, new reader, motor, trace or TPS actuator. The case
is a bounded *boundary diagnostic*; it is expected to **retain a
possible refusal on the MOVE start edge**. Merely getting past the
initial physical idle is not T1u completion and not a real-World PASS
for full continuous gait accounting.

### LocalCodex verification

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_t1v_physical_idle_dev.py \
  tests/test_t1u_gait_source_dev.py \
  tests/test_t2_gait_integration_dev.py \
  tests/test_p1_gait_dev.py \
  tests/test_t1f_t2_dev.py \
  tests/test_t1p_body_runtime_dev.py \
  tests/test_t1r_fatigue_timecourse_dev.py \
  tests/test_p1_physiology_calibration_dev.py
```

Use existing Python3.12 venv, fix any real tests/Ruff/contracts
failures without relaxing negatives; do focused then impacted FAST.
Node/Java rebuild only if required for this existing snapshot feature.
No FULL.

Run one **new disposable DEV World** after local verification,
using original T1e CLI parameters and verified binary SHA:

```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.t1e_native_dev \
 --cases t1v_physical_idle_loop --loop-moves 2 --node-trace off \
 --output /NEW/ABSOLUTE/T1V-001 \
 --paper /VERIFIED/PAPER.jar --plugin /VERIFIED/PLUGIN.jar \
 --bootstrap /VERIFIED/BOOTSTRAP \
 --confirm T1E-DISPOSABLE-DEV-ONLY
```

Check exact actual arguments before running. Preserve each new World
and its native/Paper/commands/t2/report and external SHA manifest.

### Independent result interpretation

- *Physical initial idle*: if a real consecutive admitted pre-Action
  pair meets all criteria, record `PHYSICAL_IDLE_DEV` and confirm
  one P1 transition and one M0 basal posting. Do not count as
  `WAIT_DEV`, R-qualified recovery or new S49 Action.
- *Onset*: unless authentic applied gait for the source interval
  can be established, the current provider must **latch refusal**.
  Keep original UNKNOWN outcome/clear/custody, do not restart from a
  new anchor, zero/skip tick or fabricate hidden WAIT.
- *Second MOVE*: claim 2/2 continuous gait only after source-bound
  all intervening ticks are accounted under a justified single
  physical P1 law and the existing M0 owner, with independent replay.
- A case with initial rest fixed but onset unresolved is a narrower
  engineering advance with classification
  `DEV_WORLD_OBSERVED / NATIVE_GAIT_UNVERIFIED`, NOT an integrated
  T1v PASS.
- KEEP all T1u 4 World/802 originals and old T1q/r/s immutable.

## Next modeling task

For Action-start and post-clear residual transitions, distinguish:
- What the *WorldBody physically did* (Paper movement counter/pose,
  speed attributes, physically applied controls in the already
  timestamped callback);
- What effective motor gait was applied **during the World tick**
  (not inferred solely from command request/late Node state);
- Which part of that tick was loaded vs recovering, potentially
  mixed-mode if the control edge fell inside the tick.

Do not force a single full-tick JOG load or full-tick WAIT recovery
from endpoints with an unknown within-tick transition time.
Investigate an authoritative per-tick applied-mode receipt in the
existing Paper owner, or a bounded uncertainty interval that keeps
the physical P1 actual value unknown until resolved. Unknown cannot
produce an exact P1 receipt or Action permission. If the original
P1 physics API needs extension, preserve the old blob and make an
explicit owner-reviewed opt-in model change instead of a silent
second gauge.
