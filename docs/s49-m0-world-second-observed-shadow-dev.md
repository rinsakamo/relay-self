# RelaySelf — M0 normalized World-time basal shadow with real Paper tick custody

2026-10-26 · **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

**Exact runtime-tested source HEAD:** `c1ccabda9898c198d6d703f896893d2370dd64d9`  
**[Real isolated Paper Minecraft 1.21.8 run #40328351891 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40328351891)**.  
Branch `self/dev-s49-forward-motor-admission-20261026`.

## Scope: unit choice, not a new energy bank

The existing B0 `MetabolismConfig.basal_cost=0.5` and
`move_cost=0.25` are per **M0 logical step**. In the current
S49 DEV integration exactly one canonical M0 MOVE step is posted for
each original native S16 terminal Action, not for each elapsed Paper
World tick. We do not redefine this canonical unit or edit its
`B0EnergyLedger` mutation logic.

New isolated opt-in `--m0-worldtime-shadow-dev` is guarded by
`S49_M0_WORLDTIME_SHADOW_DEV_ONLY=1` and the existing
`--node-physics-dev --post-release-dev --native-edges-dev`
source checks. New **pure function** module:
`adapters/mineflayer/s49_m0_world_time_shadow_dev.py`.
It takes previously reviewed original S49 native Action/Paper tick
bracket, passive post-release Paper tick evidence, native ACK marker
source join, bounded Node/Paper motion footprint, and original ledger
readback. It can produce **one read-only counterfactual cost
projection**, never new M0 energy or physical Action authority.

### Normalized World time versus wall seconds

For this DEV-only thought experiment we explicitly choose:

- **20 observed Paper World ticks = 1 normalized World-second**, by
  explicit model definition, not evidence of host wall-clock duration.
- **0.5 energy per normalized World-second** as an *illustrative*
  independent basal rate. It is **NOT derived from the old
  0.5 energy per original Action**, and is not a scientifically
  measured physiological rate.
- Basal cost per observed tick = 0.5 / 20 = **0.025 energy**.
  Rate validation rejects 0, negative/nonfinite, too-large values,
  fractional/false TPS, non-20 World-tick unit and fake canonical
  calibration claims. An explicit alternative DEV rate has focused
  test coverage.
- The Paper World clock has 20 ticks per *normalized* second;
  50ms of host wall-clock time per tick, any Paper server TPS drift
  or its synchronization to Node clock is **NOT attested**.

### Why incomplete World time cannot be billed

The first native Action already has a Paper-local ARM/TICK/OWNER_RELEASE
review with every Action tick contiguous. Paper post-release observer
independently proves precisely five subsequent contiguous ticks,
on the same actor/session/world. We neither interpolate from
Node physicsTick nor infer the release tick was a sampled tick.

**Actual one-World source values:**

| Source interval | World tick IDs | Observed ticks | Basal projection |
| --- | --- | ---: | ---: |
| Original DASH Action Paper callbacks | 248–260 | 13 | 0.325 |
| Paper release marker, **no elapsed sampling callback** | 261 | **0** billed | not billed |
| Passive Paper post-release callbacks | 262–266 | 5 | 0.125 |
| **Producer-local observed total** | two non-overlapping intervals | **18** | **0.450** |
| Normalized World time represented | 18/20 World-second | 0.900 | illustrative |

These 18 covered tick ordinals are disjoint; the **one unsampled
release-boundary tick is explicitly reported, not billed**.
No duration-based scaling is applied to the second original
native Action because there is no corresponding independent
per-Action Paper bracket for it in this DEV run.
The active and passive intervals are not misrepresented as a
fully observed 19-tick span or 0.95 normalized World-second.

Original native S49 owner actually executed **two S16 native OUTCOMEs**,
and original B0 owner posted:

| Original canonical charge | Native Action 1 | Native Action 2 |
| --- | ---: | ---: |
| Basal per original M0 logical step | 0.500 | 0.500 |
| MOVE per original M0 logical step | 0.250 | 0.250 |
| DASH extra from original verified P1 | 0.08633238849 | 0 |
| M0 body tick | 0→1 | 1→2 |

Original energy **12 → 11.163667611509306 → 10.413667611509306**.
The shadow adds **zero additional actual debits**; report flags
`world_tick_basal_posted=false`,
`legacy_action_m0_replaced=false`,
`double_charged=false` and
`original_energy_remaining_unchanged=10.413667611509306`.
P1 post-release recovery, M0 idle posting, source-certified physical
WAIT, independent host/world clock trust and R/SCI admission remain
false. The 0.450 projection and 1.000 legacy total basal are
**different time coverage/units** and cannot be used as directly
comparable experimental outcomes.

## Validation

[Run #40328351891](https://github.com/rinsakamo/relay-self/actions/runs/40328351891)
included Python 3.12 focused tests plus extensive World-interval/rate
negative cases, Ruff, Node 22 native bridge tests, Java 21 pinned
Paper plugin build, original S49 sole native reader/issuer and
2/2 issued Action OUTCOME, Paper positive DASH modifier 11/13
callbacks, original P1 single-fatigue replay and verified canonical
M0 owner postings. Python coverage: explicit rate/unit errors,
false clock synch claim, missing/overlapping/discontinuous World
intervals, forged session/action, unsupported source class, mismatched
M0 sequence and energy, invented WAIT/P1/M0 charges, wrong release
marker, and incorrect ledger reconciliation.

**Initial CI run [#40328103350](https://github.com/rinsakamo/relay-self/actions/runs/40328103350)
FAILED** before World launch from one unused test import. Removed that
import; next exact source HEAD ran all checks and real World
successfully. The failure was not rewritten as success.

## Remaining engineering limits

This is an **accounting-unit contract demonstration**, not a
production-worthy metabolism rule. Real-time energy rate selection
must be empirically/architecturally chosen; if Minecraft World tick
rate is sped up or slowed down, normalized World seconds diverge
from real human seconds. The Paper producer-local samples are
source-joined but not a global WorldTick authorization ledger.

Before replacing the canonical M0 owner calculation, implement
unique, gap-checked tick custody **for all relevant original
Actions and inter-Action intervals**, including second Action;
establish the rate for basal and MOVE in the same units; prevent
reusing any World tick in more than one category; and authorize
an explicit migration from per-Action charges to per-tick charges
without double posting. Until then **shadow only**.

main, PR #545 and PR #634 are unchanged; FULL/SCI/R not executed.
