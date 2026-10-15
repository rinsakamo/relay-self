# M0.2 — Editable Minecraft exhaustion physics / explicit three-factor rates

**Owner:** M Lane #616 / existing Draft #617.  
**Implementation ceiling:** OFFLINE_SPEC_AND_REFERENCE_ARITHMETIC_ONLY.
This change DOES NOT install/execute a Paper plugin, alter a Minecraft World,
change S51/Action policy, calibrate biology, or qualify a new live experiment.

## Decision

Use **the Minecraft Server's food, saturation, exhaustion and health** as the
single authoritative body state. M0.2's offline arithmetic is **not** a second
energy balance: it is a reference for applying/reviewing exhaustion adjustments.
Do not combine M0.1's energy debits or M0's E=20 bookkeeping with live food
drain. Original B0/M0/M0.1 source bytes and frozen receipt authority remain
historical evidence, not automatically promoted M0.2 science.

All controls are editable *in one file*:
`experiments/config/m02_relay_ecology_v1.json`.
Every Paper 1.21.8 `ExhaustionReason` plus synthetic `BASAL`, `COGNITION`
has an explicit `unit, standard, multiplier, additional, enabled` entry.

For each action kind a:

```
X[a] = quantity[a] * (standard[a] * multiplier[a] + additional[a])
```

The exception is only a **source-defined dynamic standard**: if the actual
Vanilla amount depends on potion/environment/unknown origin, then explicitly
`standard: "native"`, and the original observed event amount is used for
one event. This still uses the same formula with q=1; no made-up zero is
substituted. `enabled: false` is allowed only for `COGNITION`.
Reject negative, infinite, NaN, invalid units, missing cause or profile fields.

## Initial candidate values (NOT ecologically calibrated)

| Kind | Unit | Standard exhaustion | Status |
| --- | --- | ---: | --- |
| BASAL | world tick | 0.001 | **Candidate injected non-Vanilla rate** |
| WALK | block | 0.01 | **Candidate injected non-Vanilla rate** |
| CROUCH | block | 0.0 | Vanilla-like |
| SPRINT | block | 0.1 | Vanilla |
| SWIM | block | 0.01 | Vanilla |
| JUMP | event | 0.05 | Vanilla |
| JUMP_SPRINT | event | 0.2 | Vanilla |
| ATTACK | event | 0.1 | Vanilla |
| DAMAGED | event | 0.1 | Vanilla |
| BLOCK_MINED | event | 0.005 | Vanilla |
| REGEN | original native event | native | Preserve observed exhaustion; no inferred HP delta |
| WALK_ON_WATER | block (cm events) | native | Native per-cm amount; editable addition per block |
| WALK_UNDERWATER | block (cm events) | native | Native per-cm amount; editable addition per block |
| HUNGER_EFFECT | original native event | native | Dynamic / potion-dependent |
| UNKNOWN | original native event | native | Dynamic / do not invent source |
| COGNITION | admitted unit of work | 0.0, disabled | No cognitive energy cost |

Source: Minecraft Java Edition exhaustion reference:
https://minecraft.wiki/w/Hunger and
Paper 1.21.8 `EntityExhaustionEvent.ExhaustionReason`:
https://jd.papermc.io/paper/1.21.8/org/bukkit/event/entity/EntityExhaustionEvent.ExhaustionReason.html

`standard` is **always written next to its two adjustable parameters**.
The sample profile is named `relay-ecology-v1-candidate` and marked
`candidate_uncalibrated`, so nobody may interpret its BASAL/WALK values as
measured real-world or production-ready coefficients. The normal baseline for
vanilla idle/walk is zero. Other numbers match cited gameplay tables, but
must still be confirmed on the selected version/build and specific Paper source.

## Movement abstraction — 2026-10-15 user-approved

A **Self MOVE/SEEK steering decision is nominally up to one Minecraft block**
(1 block = 1 nominal meter), NOT one decision or Action per centimeter.
The existing S50 `SeekWaypoint.max_step_m=1.0` is already the default cap;
do not change current S49/S50 Action permission/issuance or simulate 100
individual Action calls to cover one block. A waypoint may intentionally
request less than one block if closer to the target, and a blocked Action may
move less or not at all. One block is an **action planning resolution/cap, not
proof that every issued Action produces exactly 1.0m displacement**.

The Paper server retains its native **per-centimeter** movement exhaustion
accounting. With M0.2 WALK standard `0.01 exhaustion/block`, each **observed**
1cm WALK exhaustion event contributes `0.0001`; 100 such events total
`0.01`, and 40 such events total `0.004`. Never round each observed
centimeter to a whole block, never charge a requested/failed one-block
distance, and never levy an additional charge for the single Self choice.
World tick BASAL is charged once per actual tick throughout the action, no
matter how many native motion events occur.

These are unit-integrity examples rather than direct native-source proof:
Paper events, locomotion cause transitions and actual traveled distance
must still be verified in disposable World evidence.

## Future Paper 1.21.8 application contract (S/R-owned)

- **One action -> one cost:** For original `EntityExhaustionEvent`, read
  `event.getExhaustion()`, then **REPLACE** using
  `event.setExhaustion(X)`. Never `addExhaustion(X)` on top of the
  automatically pending native expense. Do not also bill these events into an
  independent M0 energy ledger. Other server plugins may alter/cancel the event;
  require isolated dedicated World and a documented event listener priority.
- **Movement unit conversion:** Paper's `WALK`, `CROUCH`, `SPRINT` and
  `SWIM` reasons fire per **centimeter**; the profile is per **block**:
  `quantity_blocks = observed_centimeters / 100`. 1 cm of WALK with
  standard 0.01 / block => 0.0001 exhaustion, NOT 0.01.
  `WALK_ON_WATER` / `WALK_UNDERWATER` are also per-centimeter events.
  Their standard is the original measured per-cm exhaustion, while the
  editable addition is per block (`native*multiplier + additional/100`).
- **REGEN:** use native exhaustion per actual REGEN event. The Paper
  exhaustion event does not itself attest HP healed. Never invent that delta.
  A future explicit per-HP profile requires separately qualified measurements.
  Paper event kinds are not the same as Self Action kinds.
- **BASAL:** an S/R server owner scheduler charges **once per actual World
  tick**, exactly once per participating player, regardless of L0/L1/L2
  decisions, pauses in an agent controller or real wall-clock slowness.
  A paused/stopped World accrues zero World ticks. It must not run in the
  ExhaustionReason listener (no such native BASAL reason).
- **COGNITION:** `enabled=false`, `standard=0`, `additional=0`;
  future optional, source-authenticated incremental computation/work bill
  only, with base energy already covered by BASAL. No approximate GPU joule
  conversion or L2 token tax today; L0 continues concurrently.
- **Native/dynamic causes:** Preserve the *observed native event amount* by
  default, do not silently treat UNKNOWN as zero or ignore Hunger effects.
  Failed provenance or unexpected enum entries require explicit diagnosis;
  do not grant Self or M0.2 alternative control over source events.
- **Food:** standard `cooked_beef` (steak), Vanilla food +8 and maximum
  saturation gain +12.8 when not capped; not 1 Joule or 1 M0 energy unit.
  The World manages saturation cap, depletion, regeneration and starvation.
  M's offline cost diary does not credit food or change health.
- **Starvation/respawn:** HP deaths and physical lineage terminal policy
  require a separately specified S/R World rule. Standard Minecraft respawn
  resets food state, so M0.2 does NOT by itself prove M Lane's historical
  starvation-only permanent termination or no-free-refill condition.
- **Source identity:** pin server build, plugin SHA, exact profile SHA, seed,
  tick clock, non-overlapping cause/event IDs and original event amounts.
  A change to any `standard`, `multiplier`, `additional` or unit changes
  profile SHA and is a new physical experimental condition; not live-editable
  by Self. G may propose inherited individual parameters later through a
  separately owned World physical initialization contract.
- **Unknown timing:** M0.2 offline `AuditState` intentionally requires
  consecutive World tick for basal accounting; it must not interpolate
  missing ticks from wall-clock, old S51 snapshots, or decision counts.
  Event IDs and sessions fence replay/duplicates, but an event ID string is
  NOT native source authentication.

Reference API:
https://jd.papermc.io/paper/1.21.8/org/bukkit/event/entity/EntityExhaustionEvent.html

## Execution / review status

```bash
python -m pytest -q tests/test_metabolism_m02_exhaustion.py
```

Scope of checks: profile completeness, deterministic hash, explicit default
standard values, positive/negative multiplier and additional controls,
centimeter conversion, native REGEN units, cognition OFF/ON gate, native event
passthrough, source-shape fail-closed, consecutive World ticks and exactly-once
event IDs, duplicate key / nan profile rejection. Ordinary repo CI also
regresses M0 and M0.1.

Next ownership boundary:
1. **M:** justify BASAL/WALK candidate values against measured food/exhaustion
   conditions and independently chosen ecological reference. Freeze variants.
2. **R:** isolate **new** Paper 1.21.8 World profile; leave existing vanilla
   Golden/World intact. Qualify source events, clock, plugin and cleanup.
3. **S:** add opt-in disposable DEV-only integration using existing S49/S51
   owner route (no competing launcher), standard steak feed and correctly
   authenticated body observations.
4. **V:** independently preregister policies/physics comparisons. No M0.2
   physical qualification, cognition gain, learning advantage, or scientific
   success is claimed by M offline CI.

Current ceiling:
`M02_OFFLINE_PARAMETERIZED_EXHAUSTION_CONTRACT /
SOURCE_ORIGINALS_NOT_CONNECTED / ECOLOGICAL_CALIBRATION_PENDING /
REAL_PAPER_WORLD_NOT_RUN / SCIENCE_NO_GO / PRODUCTION_NO_GO`.
