# RelaySelf G4.12 DEV — original S49/G44 ACK source boundary and Paper generation dwell (2026-10-30 JST)

## Purpose and non-claims

G4.11 found **9 control-boundary-different Paper pairs** in its prior real controlled World (different run). G4.12 does **not** force this prior count into a new World. It traces each *current World's* G411 `ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS` row to the original typed S49 motor APPLIED ACK or same-original-S49-Action G44 transition ACK, checks original S15 CLEAR is still *after* the selected Paper frame, and reports how many consecutive **already captured** Paper WorldTicks retain that exact Node effect/generation/phase. The result is **observation dwell**, not the physical motor duration or packet-to-tick command acceptance.

Strict default-OFF `--g412-original-control-boundary-dwell-dev` plus `S49_G412_BOUNDARY_DWELL_DEV_ONLY=1` requires the existing G411/G410/G49 stack. Pure `join_g412_original_control_boundary_dwell_dev()` recomputes the entire G411 and G49 audits from unchanged original Paper/G1/T2/G48/G410 and original S49 applied/clear ACKs, validates typed G44 ACKs (same parent S49 Action, effect ID, requested mode, native probe and ACK ordering), and selects only the G411 original control-boundary rows. No information is taken from a secondary native reader or new Paper sample. Failure is fail-closed.

The derived `g412_original_control_boundary_dwell_dev.json` carries SHA256 of the original G411/G410/G49/T2 whole-file sidecars and individual G411/G49/T2 source rows; the original report records the derived file SHA. `ORIGINAL_S49_APPLIED_EFFECT_OBSERVED` / `G44_SAME_S49_ACTION_SUBEFFECT_OBSERVED` describe correlated Node/Paper evidence **after** a native effect ACK, not native packet-acceptance exactly at that Paper WorldTick. Any uncorrelated boundary remains `UNKNOWN_UNCORRELATED_NODE_BOUNDARY`. Original CLEAR is a future boundary for each selected in-Action frame, never reclassified as having physically cleared already.

The measured contiguous-generation count is bounded by already captured original Paper intervals, the same Node action/effect/generation/phase identity and the native original APPLIED→CLEAR bracket. It does **not** prove polling/physics cadence caused the unstable G1 kind. Null or absent action/effect/mode fields in original INITIAL/CLEARED Node frames are valid observational states (not forged MOVING effects), with dedicated regression tests.

No change to original S49 Action policy, input timing or motor, Paper plugin, native reader, synchronous trace, G1 source, T2/P1/M0 owner or debit, WAIT credit, source admission, G49/G410/G411 UNKNOWN or any existing protected evidence.

## Reproducible code heads and completed tests

- Isolated branch: `self/dev-g412-original-control-boundary-dwell-20261030`.
- Parent G411 report HEAD `3f32db71d71190f3e408269379334f219223f362`.
- **Exact code/workflow physically tested SUCCESS HEAD:** `03d490c0fa0731d9a9f0412bab01aeb837bcabaf`.
- [Three real disposable Paper Worlds #40992856461 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40992856461), [original run artifact #12950560497](https://github.com/rinsakamo/relay-self/actions/runs/40992856461/artifacts/12950560497). Pinned Paper 1.21.8, Java21, Node22, Python3.12 focused/Ruff and existing plugin builds completed.
- **Subsequent regression-test-only HEAD:** `7b56d13dae46fa4d79a7d715686cf6da0352cdf4`. Between physical SUCCESS and this SHA the **only changed file is `tests/test_s49_g412_original_control_boundary_dwell_dev.py`** (20 lines: explicit INITIAL/CLEARED nullable metadata positive/negative test); no application, motor, diagnostic algorithm or workflow changes. [Focused CI #40992881904 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40992881904), **60 pytest PASS**, Ruff and compileall PASS.
- **Retained unsuccessful results:** [#40992340873 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40992340873) initial Ruff I001; [#40992533513 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40992533513), [artifact #12949752791](https://github.com/rinsakamo/relay-self/actions/runs/40992533513/artifacts/12949752791): controlled World itself reached Goal, but G412 postrun refused valid nullable original Node boundary metadata; fixed only new read-only G412 serializer validation. [#40992881808 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/40992881808), [artifact #12950510695](https://github.com/rinsakamo/relay-self/actions/runs/40992881808/artifacts/12950510695): this later test-only-head World passed the G412 controlled source join, but its separate **hazard World failed on original S49 Action #1's unsafe native S16 terminal before zombie stimulation**; original T2 correctly refused credit; **not a G412 diagnosis result or full three-World success**. These trials were not retroactively relabeled as PASS.

## Successful physical observations: #40992856461

| World | Original outcome | Original T2 and source-bound G4.x evidence |
|---|---|---|
| G4 baseline no G412 opt-in | Goal REACHED in **6** original S49 Actions; final error **0.381034118m** | **57** original T2 WorldTicks; G412 OFF |
| Controlled G412 | Goal REACHED in **6** original S49 Actions; final error **0.426744374m** | **132/132** original T2/P1/M0 ticks unchanged/SHA-bound. Original G47/G48 **9** bounded candidates / **123 UNKNOWN**. G410 **13** in-Action UNKNOWN, G411 **13** nonstable G1 rows, and G412 **8** ACK-linked control-boundary rows. |
| Native zombie hazard | Original RUN→JOG transition ACK **seq62**, genuine zombie detected **seq67** at **0.688260m**, original CLEAR ACK **seq68** → original S16 **seq69** UNKNOWN/FAILED. No additional S49 Action. | Original T2 owner refused unsafe S16, **32/32** prior T2 receipts preserved, **P1 credit 0**. Original G49 **30 UNKNOWN/2 stable**; G412 **3** control boundaries (2 original S49 effect and 1 G44 subeffect), source-bound to existing 32 T2 ticks. |

**Controlled eight source-bound G412 rows (exact native ACK + Paper effect identity):**

| Source-correlated boundary | Count |
|---|---:|
| Original S49 APPLIED effect observed | **6** |
| G44 gait subeffect within the **same** original S49 Action | **2** |
| Uncorrelated boundary requiring inventing an effect | **0** |
| **Total** | **8** |

Their contiguous Paper WorldTick generation spans (in selected-row order) were **[4, 4, 1, 1, 3, 1, 4, 4]** — range **1–4** captured WorldTicks. These are source-observation spans, **not** precise physical acceptance durations, player speed control latencies, or G1 stable gait qualification. In this run G411's eight source-bound boundary rows were a subset of its thirteen G1-nonstable rows (the other five were not force-assigned). All original G49 **123 UNKNOWN remain 123**, and original T2 source identity, one P1/M0 owner, native Action S15/S16 termination and accounting are unchanged. Separate baseline and controlled goal errors are not a causal performance comparison.

**Hazard G412 rows:** 3 selected source-bound boundaries (2 original S49, 1 G44); Paper generation spans [3, 2, 2] captured ticks. Native zombie path remained original source-owned, and unsafe S16 was correctly refused by the original T2 accounting owner with no WAIT/P1 recovery.

## Gate and next

**`DEV_ONLY / G412_REAL_PAPER_THREE_WORLDS_PASS / ORIGINAL_S49_G44_ACK_CORRELATED_PAPER_DWELL / ORIGINAL_G49_G410_G411_UNKNOWN_UNCHANGED / ORIGINAL_T2_P1_M0_SHA_PRESERVED / ZOMBIE_S16_UNKNOWN_T2_REFUSED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`**

G4.12 makes **no** claim of per-physics-tick packet acceptance, effective speed, exact lag attribution, motor causality, R QUAL qualification, L learning, V SCIENCE, or physical improvement. No FULL, main merge, Draft #545/#634 adoption or force push, new LLM/GPU execution.

Potential G4.13, if useful: analyze existing original G1 stable-kind occurrence within these bounded **1–4** source-generation spans and the existing G46 post-control challenge, without adding input holds or treating source dwell as physics tick certification. This is an optional observational step, not a reason to postpone L Lane's actual learning.
