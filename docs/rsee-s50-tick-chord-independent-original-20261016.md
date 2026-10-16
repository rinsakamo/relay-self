# RSEE #575 — prospective S50 native tick-chord WALK originals (2026-10-16)

**Classification:** `R_S50_FIVE_NEW_PAPER_TICK_CHORD_ORIGINALS_DEV_REVIEW_ONLY`.
R owner Draft #610. Source S Draft #545. No new R Java/Node/GPU launch,
no QUALIFICATION grant used, and no V/SCIENCE run.

## Motivation and independently reviewed source

S owner newly implemented `s50-tick-meter-dev: true` in disposable
Paper 1.21.8 Worlds. Instead of depending on `PlayerMoveEvent` events
—which omit some small player movements—the plugin records a prospective
native **one-per-World-tick** observed source horizontal chord and calls
`Player.setExhaustion` for the corresponding WALK request.
The old `M02_DEV_MOTION` callback still observes packets but is **zero-billed**
to prevent double billing. This is a genuine physics write-input, not a
supposed continuous sub-tick path or independently quantified downstream
food/saturation effect.

Source 5-arm DEV owner is immutable
[S run #38899196206](https://github.com/rinsakamo/relay-self/actions/runs/38899196206),
exact S source HEAD `45102435ada2ecf2cbe2c8bf2277731122dfbbf4`,
single workflow attempt, 5/5 DEV owner SUCCESS. The individual native
original GitHub artifacts are 12044573785 / 12044868239 / 12045486950 /
12044913364 / 12045621422 for BASE_ON / SHAM_ON / BASAL_ZERO / WALK_ZERO /
BOTH_ZERO respectively, with separate GitHub archive SHA digests.

R **independently** fetched the original five S artifact contents (not a
copy of S's summarized report), verified exact run HEAD/attempt, five job
conclusions, artifact names/IDs/API digests, source log/native/Action journal
original-byte hashes in the per-run report, source plugin JAR SHA, Action
identity, native ACK chronology, Paper World time/pose/cumulative write
integrity, BASAL first 200 living-player writer callbacks, source
`level.dat` NBT seed=61021, event zero-charge, bounded physical quiet
observation, native STOP and claimed Java/Node exit0/port release.
**Host PID absence is only reported by S**, not separately witnessed by
R. GitHub artifact API digests authenticate provider metadata; the R
per-file checks independently reconstruct original contents, but the R
Python parser does **not** itself verify the raw ZIP compressed bytes.

R [independent re-read #38904112037](https://github.com/rinsakamo/relay-self/actions/runs/38904112037)
**SUCCESS**, archived five originals + independent receipt for 90 days:
[artifact #12046039949](https://github.com/rinsakamo/relay-self/actions/runs/38904112037/artifacts/12046039949),
archive ZIP reported SHA256
`7cc1419bf3a61d96eb93c0326820393d04035528c3910eb232dfef1b75249ed8`.
Source plugin JAR SHA matched all five:
`a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f`.
It is **not** the previously R-qualified old JAR.

| Arm | Paper tick writer rows | Source tick-chord block sum | WALK `setExhaustion` input | First 200 BASAL inputs |
|---|---:|---:|---:|---:|
| BASE_ON | 179 | 1.9389928412050272 | 0.019389928412050277 | 0.2 |
| SHAM_ON | 184 | 1.7231471919306607 | 0.01723147191930661 | 0.2 |
| BASAL_ZERO | 179 | 1.9389928412050272 | 0.019389928412050277 | 0 |
| WALK_ZERO | 184 | 1.9389928412050272 | 0 | 0.2 |
| BOTH_ZERO | 181 | 1.7231471919306607 | 0 | 0 |

All rates agree with source `0.01 exhaustion/tick-chord block` or
zero and `0.001 exhaustion/player callback` or zero as configured.
For every arm, Paper `PlayerMoveEvent` observed distance is smaller
than tick-chord source distance, and event-based billing stays zero.

## Absolute scientific and qualification limits

This does **not** prove true continuous movement between two Paper tick
poses; a chord is the minimum path length. It does not prove that no
other body/motion cause acted between ticks, independently prove actual
net food/saturation consumption or finite food viability, or establish
permanent physical stop beyond the bounded observed quiet interval.
Source native STOP and S host cleanup receipt do not automatically
establish a separate R host PID/port witness.

S's new JAR/config were used only in **DEV**. Do not upgrade these
original five DEV sessions into QUALIFICATION; that would fabricate a
grant/run and defeat prospective evidence. User-authorized fresh
new-JAR one-shot QUAL permission remains unconsumed. The old spent
2026-10-15 permission cannot be reused. The new plugin has not been
independently engineering-qualified on any updated profile.

V7's frozen matched-path tolerance `0.005 block` is not met:
the new five-arm observed chord spread is ~`0.2158456493 block`.
Do not select favorable paths or normalize the measured paths into
paired-effect evidence; V7 science 0/20, V6 0/48, G3/production NO_GO.
These five DEV source results are distinct from previous failed
fixed-pose and originally frozen DEV attempts.

### Implementation and reproducibility

- R independent parser:
  `experiments/standard_env/s50_tick_chord_original_audit.py`
- Synthetic fail-closed/negative tests:
  `tests/test_rsee_s50_tick_chord_original_audit.py`
- Exact-run original GitHub readback + 90-day evidence:
  `.github/workflows/rsee-s50-tick-chord-five-arm-readback.yml`

All three are in existing R Draft #610 only. S stays S action owner.
The workflow never launches Java/Node/World and issues no qualification.
A **new physical QUALIFICATION**, if later executable, must verify exact
current stable S HEAD and source JAR/config, world/control gate, one new
grant+run identity, independent PID/port/STOP and original bytes, then
publish a fresh scoped R verdict without confusing source-shape
accounting with ecological or scientific efficacy.
