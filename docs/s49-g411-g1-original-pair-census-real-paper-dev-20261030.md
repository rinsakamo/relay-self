# RelaySelf G4.11 DEV — existing G1 original adjacent-Paper-pair evidence census (2026-10-30 JST)

## Boundary and design

Parent G4.10: final report HEAD `a29e64cf5285f42792d5d022a23459faf8616bee`, physically tested code `f5365383976b91e755e84152be92035f6d0a0a56`. G4.10 identified original in-Action UNKNOWN that had no G1 stable two-frame gait kind. G4.11 **does not** attempt to turn those UNKNOWN ticks into recognized gait, physical WAIT, an improvement claim, or a per-physics-tick motor acceptance proof.

The default-OFF `--g411-g1-unstable-pair-census-dev` and `S49_G411_G1_PAIR_CENSUS_DEV_ONLY=1` require the existing G4.10/G49 chain. Only after the existing native Action/S15 CLEAR/G1/T2/G49/G410 has finished, the pure `join_g411_g1_unstable_pair_census_dev()` recomputes the original G410 audit from the **same G49, G48, admitted Paper and original T2 inputs**, fails closed on inconsistent G410 rows, then reads each G410 row that explicitly lacks `G1_TWO_SAMPLE_STABLE_KIND`. For the immediate previous original Paper frame, it reports original source sequence and WorldTick deltas, Node generation/phase, applied controls, Paper gait-fact continuity, original G1 kind, delta XZ/motion counter and post-control challenge. Every selected result contains original exact G410/G49/T2 per-row SHA256. Derived `g411_g1_unstable_pair_census_dev.json` carries original G410/G49/T2 whole-file SHA256 and its own SHA256 in the original S49 report. No supplementary Paper observer/reader, extra WorldTick, longer command duration, synchronous trace, new P1/M0 owner, extra debit, model call, or mutation of prior sidecars.

**Observational classes are not causal explanations:** an adjacent WorldTick pair cannot certify physical command acceptance; differing Node generation describes a **source boundary**, not input lag; a zero-motion-with-controls G1 kind does **not** prove a collision; an absent original adjacent Paper sample (if encountered) would not prove why the sample was absent. Original G49 UNKNOWN and G410 evidence lists remain exactly unchanged.

## Exact tested source and physical DEV trial

- Isolated branch: `self/dev-g411-g1-unstable-pair-census-20261030`.
- **Exact physically tested code + workflow HEAD:** `964abbdd944c64d497402be081d1940751e374ba`. [GitHub Actions #40988945021 attempt 2 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40988945021/attempts/2), [retained real original evidence artifact #12948153396](https://github.com/rinsakamo/relay-self/actions/runs/40988945021/artifacts/12948153396).
- [Focused Python3.12 CI #40988818214 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40988818214): **43 focused pytest PASS**, Ruff and Python compile PASS. Physical workflow also passes scoped Python checks, Node22 protocol tests, original Java21/Paper1.21.8 plugin builds, and **three independent disposable real Paper Worlds**.
- **Failed evidence preserved:** [focused CI #40988676090 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40988676090) (pytest decorator syntax); [#40988766974 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40988766974) (wrong test expectation: two G410 UNKNOWN had stable G1 kind but lacked post-control challenge, so were correctly excluded). [Physical run #40988945021 attempt 1 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40988945021/attempts/1) and retained [original artifact #12948675912](https://github.com/rinsakamo/relay-self/actions/runs/40988945021/artifacts/12948675912): first original DASH Action had **no S16 terminal**, leading to G49 refusing absent original CLEAR source; G411 was **not reached**, not claimed as physical source-join PASS. Attempt 2 used the **same exact SHA** and new disposable Worlds with unchanged original motor code.

### Three real Worlds, attempt 2

| World | Original result | Original ledger and G411 |
| --- | --- | --- |
| G4 no-opt-in baseline | Goal REACHED, **3** original Actions, **38** original T2 WorldTicks, error **0.441677490m** | G410/G411 OFF |
| G411 opt-in controlled | Goal REACHED, **6** original Actions, **129/129** original T2 WorldTicks; error **0.467005798m** | Original G47/G48 **5 stable source candidates / 124 UNKNOWN**; G410 in-Action UNKNOWN **14**, all **14** lack G1 stable kind; G411 reports **14** adjacent original Paper WorldTick pairs |
| Genuine zombie hazard | RUN→JOG effect ACK **seq61**, genuine native zombie **seq66** at **0.677056661m**, original CLEAR ACK **seq67** → original S16 **seq68** UNKNOWN/FAILED, next S49 Actions **0** | Original sole T2 owner correctly refuses unsafe S16, `owner_failed=true`, **31/31** pre-refusal T2 rows preserved, P1 credit **0**. G411 checks **6** in-Action G1-nonstable rows, 6 adjacent original Paper WorldTick pairs |

In the controlled World, the **14 G411 rows are mutually exclusive evidence classes**, all source-bound to exact original G410/G49/T2 SHA:

| G411 recorded class | Rows |
| --- | ---: |
| **ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS** — original Node effect/generation or phase changed between the two existing Paper frames | **9** |
| **ADJACENT_PAIR_PRESENT_CAUSE_UNDETERMINED** — adjacent pair exists but G1 still did not yield a stable gait kind; no invented cause | **3** |
| **ADJACENT_PAPER_GAIT_FACTS_DIFFER** — original Paper sprint/sneak/modifier/speed facts differ across the two adjacent frames | **1** |
| **G1_NEAR_ZERO_MOTION_WITH_CONTROL_NOT_CAUSAL_BLOCK_PROOF** — G1 observed stalled/near-zero motion with controls; physical obstacle/collision not established | **1** |

**All 14 source WorldTick gaps = 1**, so "missing adjacent Paper tick" is **not** the observed explanation for this trial. Original 124 G49 UNKNOWN remain 124; existing 5 stable candidates, original ledger SHA/P1/M0, original 6 Action boundary receipts and single T2 owner are unchanged. No speed, efficiency, inertia or polling-cadence causal claim from independent G4 baseline and controlled World differences.

Hazard G411 classes over the same 31 pre-refusal T2 rows: **3** Node control boundary differences, **1** adjacent-pair-undetermined, **1** Paper gait facts difference, **1** near-zero-motion-with-control. All six have adjacent original WorldTick pairs. Unsafe original S16 remains FAILED/UNKNOWN and receives no P1 credit.

## Constraints / next

**DEV_ONLY / G411_REAL_PAPER_THREE_WORLDS_PASS / ORIGINAL_G410_G49_T2_SHA_PRESERVED / G1_NONSTABLE_PAIR_FACTORS_OBSERVED / HAZARD_T2_FAIL_CLOSED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

No merge/force push to main or protected Draft PR #545/#634, no FULL, R QUAL or V SCIENCE. No new motor command, physical reader, WorldTime source, runtime sensor, synchronous trace or physical gait qualification.

Next narrow G4.12, if needed: examine **9 actual control-boundary-change pairs**, split the original G44 subeffect changes from original S49 Action dispatch or CLEAR, and report the age in original WorldTicks of unchanged generation after the boundary (read-only). Avoid making the motor hold longer merely to obtain two stable frames; timing limitations are properties of this World, not an instruction to forge proof.
