# P1-D — solo fatigue comparison, prospective V **review candidate**

**Status:** `P1_D_OFFLINE_CANDIDATE_NOT_V_ADMITTED / NO_WORLD_TRIAL / SCIENCE_NO_GO`. No real World/Java/Node/GPU/LLM test, no scientific finding. P1 author proposes; **V #619 has the exclusive authority** to preregister, modify/power or reject. S #537 owns policy and Action; R #575 owns initial World clones, native original observations and qualification; M #616 controls Paper hunger physics. Research index #620. The P1 branch is stacked on unmerged M #617 and cannot be independently merged to main.

## Artifacts

- `experiments/p1d_evaluation.py`: immutable versioned proposal, deterministic seed-blocked trial roster, reference cheap REST proposals, strict all-slot accounting and **non-inferential** paired descriptive arithmetic.
- `experiments/config/p1d_fatigue_study_candidate_v1.json`: byte-readable frozen **candidate**; candidate parameters are illustrative, **not powered science**. The exact validation code rejects after-the-fact edits. V must fork/revise/freeze a distinct approved manifest *before* exposure to physical outcomes.
- `tests/test_p1d_evaluation.py`: outcome-blind synthetic + adversarial tests. Synthetic comparisons are **never** empirical results.

## Candidate design (all planned World sessions `NOT_RUN`)

Eight **new candidate** independent external World seeds (73101..73108), six arms per seed (48 candidate future slots; **not** the historical V6's 48-arm roster), up to 2400 **source-attested Minecraft World ticks** per arm. Seed-blocked arm order is deterministically SHA-ordered, not outcome-optimized. Every seed's six arms must start from **identical complete frozen terrain/chunk bytes, native XYZ/yaw/pitch, food/saturation/health, time/weather, edible item affordances and initially retained S Golden**; only declared intervention differs. Identical seed alone is NOT identical World. Realized paths, collision, rest times, death, timeout and FOOD pickup are outcomes and **must not be post-hoc matched across arms**.

| Arm | Manipulation | Causal interpretation limit |
| --- | --- | --- |
| `FATIGUE_OFF_L0` | Fatigue OFF, L0 without REST | Physics ablation; not evidence for cognition benefit |
| `ON_FIXED_L0_REST` | Fatigue ON; cheap independent precommitted REST every 20th World tick | Poor but reproducible cost control; not built into Body |
| `ON_FSM_SENSOR` | Fatigue ON, cheap sensor-only hysteresis (`>=0.7` begin REST, `<=0.3` end) | Competing state-based controller with equal sensor, no hidden true fatigue |
| `ON_L1` | Fatigue ON, actual S-owned L1 invocation/retention under same sensor | **Not implemented in this evaluator** |
| `ON_L1_SHAM` | Same S L1/controller/Body, inert toggle path | Detect toggle/instrumentation side effects; requires S implementation |
| `ON_L2` | Fatigue ON, actual S-owned L2 availability under same sensor | **Not implemented in this evaluator**; CPU/tokens/latency measured independently |

The two cheap REST selectors return **proposals only**: no Action authorization, real REST interval or opponent policy. Fatigue is independent of M0.2 exhaustion and M basal continues during physical REST. Sensor quantum/gain and Body profile must be held fixed for every Fatigue ON arm and recorded; no L1/L2 oracle gets the evaluator's true Body fatigue, hidden goals or source future. Acquisition (learning from scratch) and expression (frozen-retained-state reuse) cannot be pooled: the first candidate addresses a frozen-Golden expression comparison; developmental intervention requires another prospective design. If L1/L2 do not physically exist or the task does not discriminate, stop as `NOT_ADMITTED`, do not substitute simulated abilities.

## Actual outcome requirements, not AI reward policy

External finite food/obstacle waypoints supply **only** the physical scenario, never a hidden optimal route or internal hunger/rest directive. Primary candidate observation: **genuinely consumed edible food count through the common deadline**, with death and prior consumed food retained. Secondary true server survival ticks, observed block paths and blockage, real REST World ticks and evaluator-private fatigue, food/saturation/HP and Paper BASAL, wall/CPU/token/GPU costs. A World stopping at actual death is not `HORIZON`; infrastructure timeout is not death; unmet food opportunity is not a test success. A saturated trivial task is an *inconclusive test envelope*, not an L2 null result.

Predeclared contrasts: L1–fixed L0, L1–cheap FSM, L2–L1, L1–sham, fixed L0–fatigue OFF. Fatigue OFF tests Body physics, whereas **L1/L2 increment needs comparisons within Fatigue ON with cheap baselines**. Eight seeds and one-food-event candidate practical difference are placeholders: no justified power, confidence intervals, or significance. Do not interpret descriptive differences as science.

## Fail-closed ledger and implementation limits

Each of the 48 slots must have **exactly one** terminal status: `NOT_RUN`, `HORIZON`, `DEATH`, `INFRA_ABORT`, `SOLO_INVALID`, `SOURCE_UNQUALIFIED`. All seed/arm/session identities and failed attempts remain in the complete roster; never drop null, starving, blocked or host-failure trials. A failed slot is not a 0-food sample and cannot silently be retried or re-seeded. Duplicate sessions, missing slots, tampered plan, false HORIZON, mismatched initial-World fingerprint, fake successful REST while Fatigue OFF, invalid clock or nonfinite cost fields fail closed. Paired differences only arise from *described* physical-status slots with exactly matched pre-action World snapshot identity; missing pair remains `None`, not 0. No outcome-matching on realized distance.

A caller-provided digest (`original_source_sha256` or `world_start_sha256`) only passes **syntax/correlation checking**; the P1-D module does **not** retrieve original sources, attest the body/World source or check that each physical record truly happened. **Even if all mock slots are marked `HORIZON`, classifier stays `P1_D_OFFLINE_CANDIDATE_NOT_V_ADMITTED`, `science_go=false`**. The frozen manifest also contains `golden_freeze=NOT_PRESENT`, `r_source_admission=NOT_PRESENT`, `v_final_preregistration=NOT_APPROVED`, `science_grant=false`, `science_trials=0`. V must separately admit and independently audit actual receipts and determine causal or null conclusions.

## Gates for R/S/V and next work

1. **S**: real prospective Fatigue physical limit and REST world-interval source; actual reference L0/FSM can be implemented as S policies in existing Action authority, and existing L1/L2/sham invocation must be demonstrably equivalent except intervention. Never issue synthetic policy actions from this evaluator.
2. **R**: P1-C complete server solo census/lifecycle with original bytes and changed-world qualification; full cloned World and **native start pose/clock** parity; no 16m Mineflayer negative inference. Native STOP/PID/port cleanup, no reusing frozen Golden or spent grants.
3. **M**: M0.2 Paper's source hunger/exhaustion remains exclusive; no duplicate energy debit, no REST-free basal, no unverifiable tick count.
4. **V**: assess feasibility on separate DEV records *before* approving an outcome-blind, adequately powered final protocol; frozen intervention semantics, seeds, sample size, randomization, elapsed clock, stop, failure/censor, null, practical effect, measurement-cost and independent source review. No retroactive change to V6/V7/V8 science status.

Only after all gates and explicit new SCIENCE authority may there be any actual P1-D trial. Until then all 48 candidate slots are `NOT_RUN`, with no causal or cognitive merit claim.