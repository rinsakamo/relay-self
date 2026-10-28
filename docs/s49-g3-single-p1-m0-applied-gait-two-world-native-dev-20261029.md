# RelaySelf G3 — original T2 single P1 / atomic M0 observed DASH on real Paper 1.21.8

2026-10-29 JST. **DEV_ONLY / G3_SOURCE_BOUNDED_PARTIAL_SINGLE_OWNER / REAL_WORLD_REPEATED / FULL_NATIVE_PACKET_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Scope / exact original evidence

- Branch `self/dev-l1-t2-action-boundary-20261028`; no main or protected Draft PR changes.
- [First G3 real World SUCCESS, #40781038445](https://github.com/rinsakamo/relay-self/actions/runs/40781038445), exact source SHA `895c2a7c5946eedcf22ef9039785540a29e9717a`, [artifact #12856457576](https://github.com/rinsakamo/relay-self/actions/runs/40781038445/artifacts/12856457576).
- [Current corrected G3 real World SUCCESS, #40781645995](https://github.com/rinsakamo/relay-self/actions/runs/40781645995), exact World-tested source SHA `5dd700f0f15b5a31d03dbbceeab1b0ee08c25f0e`, [artifact #12856463099](https://github.com/rinsakamo/relay-self/actions/runs/40781645995/artifacts/12856463099).
- [Current focused CI #40781646099 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40781646099): **77 Python 3.12 focused PASS, 24 Node focused PASS**, Ruff/compile/Node syntax PASS, FULL not run.
- Separate existing Paper 1.21.8 pinned build60 and existing Paper source from T1w exact `2672d0a1fe15584d16c2426540c528410bbb8c27`; existing Paper S49 DASH plugin source unchanged. Only isolated disposable DEV Worlds.

## Architecture changes

1. `g3_applied_gait_source_dev.py`: use only **two consecutive original admitted Paper snapshots**, original Node applied controls and Paper T1u `gait_dev`, classified using the same pure bounded two-frame G1 observation. Provisional map: sneak-forward → WALK; ordinary-forward → JOG; sprint-forward (one modifier) → RUN; actual two-modifier forward sprint at Paper speed base≈0.10/value≈0.195 → DASH. This DEV map does NOT prove RelaySelf mode calibration nor accepted packet causality.
2. `t2_tick_accounting.py` remains the **sole P1 WorldTick owner** with one P1 state, monotonically advanced exactly once per consecutive original T2 source. In `g3_partial_dev` mode, stable applied gait can use `advance_gait_dev` instead of `fatigue_p1.advance`; an unknown/blocked/transition interval uses the conservative legacy **one** fatigue advance and **zero** DASH extra, not a fake WAIT. WAIT recovery only on T2's original causal S49 clear source; unproven physical-idle-only WAIT is rejected. Default OFF.
3. `b0_energy_bridge.py` new `post_g3_observed_dash_tick_dev`: **one atomic M0 state mutation per evidenced DASH WorldTick**, existing basal + measured MOVE + added DASH cost. Reject replay (same/nonmonotonic tick), invalid/nonfinite or oversized extra and insufficient M0 energy **before mutation**. No separate extra B0 debit or fictitious extra time step. Current model rate `0.20 DEV energy unit / World-second` times one 0.05s tick = **0.010 DEV energy unit** at applied power1. Existing original T2 energy owner, not an alternate Action ledger.
4. G2 real S49 goal runner has `--g3-single-owner-dev` explicit gate `S49_L1_G3_T2_DEV_ONLY=1`, plus all original T1f/T2/Paper, DASH one-shot gates. Normal/default G1/G2 P1 behavior remains unchanged.
5. `tests/test_s49_g3_t2_single_owner_dev.py`: positive DASH two-tick source, unknown transition/blocked no charge/recovery, exact one P1 and M0 tick, duplicate/replay and malformed budget failures. The nonexistent T1v physical-idle runtime import (which had only been lazy on a previously unexercised source path) was replaced by explicit **rejection** when there is no causal WAIT; no qualified rest claim.

## Actual native Worlds

| Check | First successful World (#40781038445) | Current successful World (#40781645995) |
|---|---:|---:|
| Original S49 S16-closed Actions | 3 | 3 |
| Original Goal | REACHED | REACHED |
| Final horizontal Goal error | 0.09617375003291961 m | 0.4673063193893512 m |
| Original T2 consecutive P1/M0 updates | 38 WorldTicks | 40 WorldTicks |
| Applied stable gait candidate transitions | 9 | 11 |
| Conservative unknown fallback transitions | 29 | 29 |
| Stable DASH modifier candidate ticks | 1 | 0 |
| Paper DASH modifier-positive callbacks | 3 | 2 |
| G3 DASH extra posted by original T2 M0 owner | **0.010000000000000002** | **0** |
| M0 final virtual energy | 11.940027226960021 | 11.949000485102076 |
| M0 final virtual tick | 38 | 40 |
| T2 S16 original boundary receipts | 3 | 3 |
| Owner.failed | false | false |
| R-qualified gait / per-packet WorldTick attestation | false | false |

These are **both successful physical outcomes**, not equivalent speed-matched runs. On current #40781645995, two positive Paper modifier callback ticks but zero **stable adjacent G1 applied-DASH** intervals means the source gate must refrain from posting extra charges; it did. On first #40781038445, one stable DASH candidate authorized one **model-valued** 0.010 DEV charge through the original M0 owner while original P1 advanced once. There are no double postings and no fictitious recovery on unknown source frames. Source-derived G1/T2 JSON file SHA256s were independently verified by their respective workflows; original Paper logs and producer stdout are archived, but complete original Node stdout and full disposable World image are not.

The current G3 same-World run also recorded **3** `WAIT_DEV` T2 rows after causal S49 clear, but these are not R-qualified physiological recovery proofs. Both include unobserved/unknown frames conservatively accounted as MOVE.

## Negative and corrective evidence (retained)

- Focused CI early #40780784286: Python indentation error; corrected.
- Focused #40781094675: Ruff I001 on a nested legacy T1v physical-idle import; import hoist exposed that the module is **not present** on this integrated branch (focused #40781193336). Final fix rejects uncausal WAIT rather than importing nonexistent evidence. Focused #40781315892 SUCCESS (77 Python, 24 Node).
- [Current code physical attempt #40781421276](https://github.com/rinsakamo/relay-self/actions/runs/40781421276): physically Goal reached, 41 consecutive P1/M0 ticks, 11 stable **other** gait candidates, zero stable DASH candidate. Workflow wrongly asserted a positive DASH charge even without stable source and thus FAILED, although actual no-charge behavior was correctly conservative.
- Final #40781645995 workflow instead **requires** `charged_extra == 0.01 × stable_DASH_candidate_count`, original S49 Action count matches T2 receipts, each M0 tick matches original admitted WorldTick count, source G1/T2 hashes match and all transitions remain unqualified. PASS.

## Boundaries and next work

- These are valid DEV physical **source-bound** P1/M0 postings, not independently authenticated exact Node physics-step → accepted Paper packet → WorldTick correspondences. No user grant for QUAL/SCIENCE was requested or used.
- A stable two-modifier candidate is not proof of the exact identity of all speed modifiers, and the output power1 was assumed only under this exact one-shot DEV Paper plugin and observed 0.195 movement attribute. Production G3 must bind source to the plugin's actual modifier **key and power**, not just count/value, before replacing DEV mode.
- Only stable candidate WorldTicks charge DASH. The short-window measurement demonstrably **undercharges** a physically positive modifier that never becomes source-stable, and must not be interpreted as physically complete energy accounting. Compare complete packet/Paper accepted-tick causal evidence before qualifying full coverage.
- There is one existing P1 state, not a separate physical/cognitive fatigue gauge. Existing model mode rates remain uncalibrated; no new locomotion speed governor or 20-second exhaustive DASH test in this run.
- Next G3/G4 engineering: unify accepted client packet and Paper modifier identity to minimize unknown boundary ticks, calibrate sustained mode under matched speed/starting conditions, then gate energy spending and L0 gait selection by usable confidence/tolerance. Preserve original S49 Action authority, original T2 P1/M0 single owners, default-OFF, and separate R/V permissions.

No main, protected Draft #545/#634, historical original evidence or FULL was changed.
