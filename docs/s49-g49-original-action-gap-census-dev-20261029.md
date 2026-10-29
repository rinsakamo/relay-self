# RelaySelf G4.9 DEV — original S49 Action APPLIED→CLEAR gap census for every original T2 WorldTick

Parent G4.8 DEV: `f48447a63fb39e9f9d16c7a282f5496836616eb2`, two independent 3-World real trials SUCCESS. This DEV branch does **not** change the original Action, World control, Paper/T1u callback, G1 observer, G47/G48 candidate criteria, T2 P1/M0 accounting, or source admission.

**Motivation:** In G4.8 final physical controlled World, 132 original T2 WorldTicks yielded 8 source-bound stable candidate intervals, 124 UNKNOWN. Most were outside the original RUN/G44 or direct JOG/WALK ACK windows. A gap census is needed before attempting more physical sensor sampling or reducing UNKNOWN via assumptions.

**Implementation:** gated `S49_G49_ORIGINAL_ACTION_GAP_DEV_ONLY=1` and `--g49-original-action-gap-census-dev` (requires G48/G47). Original S49 on-effect callback now records the **original typed APPLIED ACK** for every already-issued DASH/RUN/JOG/WALK Action; the existing G45 S15 CLEAR receipt bounds the exact native envelope. The passive `g49_original_action_gap_census_dev.py` joins each original G48 SHA/T2 SHA to the exact same Paper/G1 source seq/WorldTick, original T2 active action, typed original Action ACK/CLEAR and existing Node control phase. It classifies UNKNOWN as **no T2 active Action**, **T2 unbound while original Node Action ACK window active**, **before original Action applied ACK**, **after original S15 clear**, **within an ACKed DASH/RUN/JOG/WALK Action without full G48 candidate evidence**, or an explicit source mismatch. Existing G47/G48 candidate rows remain unchanged; even stable candidates still do **not** qualify full Minecraft physics tick motor acceptance or R gait.

No additional native command, callback, sampler, synchronized trace, tick source, T2 owner, M0 extra posting, or P1 fatigue/WAIT credit. The derived sidecar includes one entry for each original T2 WorldTick and exact SHA256 of both G48 prior audit and original T2 source rows. Strict duplicate/foreign Action IDs, incorrect modes/effects, nonmonotone source ticks, forged original T2 P1/M0 receipts or overlapping Action brackets fail closed. Real Java21/Paper 1.21.8 DEV workflow runs three disposable Worlds (G4 baseline, new controlled, native zombie after RUN→JOG). No QUAL, FULL or SCIENCE.

## Physical Minecraft DEV result (2026-10-29 JST)

**Exact code/workflow tested HEAD** `24b526c7a0f52faa988f7aed836f5a7427e9fb94`. [GitHub Actions #40879049892 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40879049892), [retained original artifact #12898893566](https://github.com/rinsakamo/relay-self/actions/runs/40879049892/artifacts/12898893566). Focused Python 3.12/Ruff, Node 22 29 PASS, original pinned Java21/Paper1.21.8 plugin build, and **3 independent disposable real Worlds** all passed. Initial CI #40878892420 failed on new G49 module's Python import grouping (Ruff I001); fixed without source-semantic change and preserved the failed original logs.

### World source results

- **Original non-opt-in G4 baseline:** `GOAL_REACHED`, **5 original S49 Actions**, **53 original T2 P1/M0 WorldTick rows**, final Euclidean relative target error **0.408257678m**.
- **G4.9 controlled:** `GOAL_REACHED`, **6 original S49 Actions**, **133 original T2 P1/M0 rows**, final error **0.426744374m**. Original S49 native APPLIED effect ACKs all six types and IDs preserved: DASH `set_forward_sprint_dev` seq**13**, RUN `set_forward_sprint_dev` seq**54**, ordinary JOG `set_control` seq**105/147**, ordinary WALK `set_forward_sneak_dev` seq**181/219**. Original G47/G48 sidecars have **9 source-bound stable candidate ticks** and **124 UNKNOWN**. G4.9 preserves all 133 original T2 and G48 SHA-matched entries, all 9 prior candidates, and all 124 UNKNOWN without charging anything anew.

The 133 G4.9 source-gap classifications (mutually exclusive):

| Original T2/Paper source classification | Count | What it does NOT assert |
| --- | ---: | --- |
| Existing G47/G48 source-bound stable gait candidate | **9** | Not per-physics-tick input acceptance |
| No **T2-active original S49 Action** | **105** | Does not imply physical stillness, WAIT or P1 recovery |
| T2-active but **before original applied Action ACK** | **5** | Does not imply a rejected motor; just no post-ACK bracket |
| Original APPLIED **DASH** window with insufficient gait evidence | **4** | DASH attribute or energy amount cannot be inferred without original G3/Paper proof |
| Original APPLIED **RUN** window with insufficient gait evidence | **3** | No guessed sprint |
| Original APPLIED **JOG** window with insufficient gait evidence | **2** | No guessed ordinary gait |
| Original APPLIED **WALK** window with insufficient gait evidence | **5** | No guessed sneak gait |

**Interpretation:** Of the 124 UNKNOWN ticks, **105 had no T2-active Action**, **5 preceded the corresponding Action's APPLIED ACK**, and **14 occurred within an original APPLIED→CLEAR motor window**. In the 23 source-bounded in-Action intervals consisting of 9 prior candidates and 14 missing candidates, only 9 are source-bound stable candidates, 14 remain UNKNOWN. The measured denominator of 133 T2 ledger rows is dominated by non-Action ticks in this test harness and its original G4.3 passive tail; the counts **must not** be interpreted as a 9/133 gait recognition success rate or a physical MOVE/WAIT duration. T2 P1/M0 and any native inertia may continue when no S49 Action is active. Baseline and controlled independent Worlds differ in spawn and timed observation schedules; no speed/efficiency claim is supported.

- **Native hazard:** original Step2 RUN→JOG mid-Action ACK **seq61**, genuine zombie Mineflayer observation **seq66** at **0.677056662m**, L0 INTERRUPT, original S15 CLEAR ACK **seq67**, original S16 **seq68** terminal `UNKNOWN` / consequence FAILED. **No later S49 Action**, original sole T2 owner correctly fails closed (`owner_failed=true`), **no P1 credit** and no second M0/P1 owner. **31/31 previously accounted original T2 WorldTicks** have their exact T2 and G48 source-bound hashes audited by G49; 31 UNKNOWN all preserved (18 no active, 7 pre-Action ACK, 4 DASH, 2 RUN), and zero claimed stable gait. A hazard run is not a successful T2 handoff.

All G4.9 source joins were derived **after** original T2 bookkeeping and use only previous original S49/APPLIED/S15 CLEAR/G1/T1u/Paper and G48 results. No extra Paper callbacks, physical Action, dedicated reader or writeSync. Positive/negative unit tests reject duplicate or missing native Action ACK, forged original effect/mode, ACK after CLEAR, tampered original P1/T2 SHA, changed Paper/WorldTick and overlap. No QUAL/FULL/SCIENCE executed.

### Decision and next step

**G4.9 DEV source-gap census PASS**. Observability work should now concentrate on the **14 in-action UNKNOWN** ticks in this run (particularly the 4 DASH and 5 WALK), not the 105 non-Action ticks; any future physics-accuracy work must distinguish intrinsic input acceptance and inertia from already-posted P1/M0. Next G4.10 suggestion: build a **read-only in-Action evidence quality matrix** for these 14, reporting exactly which after-control challenge, stable G1 pair and native Paper modifiers fail and optionally qualified DASH input if the existing G3 original source supports it. Do not increase control pulse durations just to improve evidence, invent source ticks, or grant P1 recovery from unbound intervals.

**Classification:** `DEV_ONLY / G49_REAL_PAPER_WORLD_PASS / ORIGINAL_ACTION_APPLIED_TO_CLEAR_SOURCE_GAP_CENSUS / ALL_133_T2_SHA_BOUND / P1_M0_UNCHANGED / ZOMBIE_CLEAR_S16_UNKNOWN_T2_REFUSED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
