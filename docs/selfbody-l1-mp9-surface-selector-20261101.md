# RelaySelf MP9 — source-conditioned body-experience model selection (DEV)

2026-11-01. Stacked on [MP8 Draft #661](https://github.com/rinsakamo/relay-self/pull/661). MP8 physically matched normal vs ice but failed the prespecified environment-specificity gate: its MP7-fit ICE coefficient slightly outperformed the old normal coefficient even on GRASS_BLOCK; Last beat the ICE fit on ICE. This is a negative result, not a reason to silently reclassify MP8.

## Main hypothesis, scope, and frozen inputs

**Question:** Can the actually observed underfoot Paper material, combined with experience fitted separately from MP8 normal/ice Worlds, select a different one-step motion model prospectively, and outperform a single fixed model on new heldout normal/ice Worlds?

- MP8 source pinned to Git blob SHA-1 `24d38edd73ab1bebd61c7d9819e53fea7f1863b8`, real run `41279293497`, exact physical executing HEAD `180967d162481336e9b306dcebc7dac06e312db6`, **not** MP9 target data.
- The MP8 eight WAIT displacement samples per surface fit `x[t+1] = c_surface * x[t]` by nonnegative least squares through origin, exactly seven transitions each. Expected `c_normal≈0.57013324771056`, `c_ice≈0.60521934696537`. Both coefficients **must be frozen before** either MP9 World is created; source or train World mismatch fails closed.
- The actual MP9 surface cue is `S50_DEV_SURFACE_LOCK` from original Paper 1.21.8; the host accepts it only after unique marker/World/subject/material/onGround/source checks. Then (before the unchanged original S49 native MOVE) it writes `MP9_SHADOW_SELECTION_FIXED` to the existing observation journal. This is a bounded readonly prediction shadow, **not** the authoritative SelfBody view, independent Goal, new S49 Action, L1 policy learning, or S10/S11/L10 admission.
- Default OFF `--l1-mp9-shadow-dev`, requires the existing explicit MP8 Paper material mode and original Paper frozen model. No new issuer, no real LLM, no GPU, no override of original L0.

## Proposed Stage 1: exactly two new disposable original Minecraft Worlds

1. Use the pinned Java21 Paper 1.21.8 build60, Mineflayer 4.39.0, original Paper/plugin/server, single S49 Action per World and original S16 clear/OUTCOME. Explicit once-only DEV release and separate fresh output directories. MP8 fixed seed is **not reused**: MP9 declares `RelaySelf-MP9-Heldout-20261101`, controls initial teleport/landing and verifies actual pre-Action ground/pose/velocity/health/food/seed in both World originals. The two source lock ticks may differ; only sampled pre-Action matching can be accepted.
2. New NORMAL World, original grass 5×5 verification and material `GRASS_BLOCK`. New ICE World, same grass preflight and exactly 25 PACKED_ICE block changes before Action. Original underfoot 8 samples each, 7 original Paper-local old baseline future scores, and captured S49/Paper original outputs.
3. The host selects the appropriate MP8-fitted coefficient **after material readback, before S49 native Action** and leaves an original journal ticket. The MP9 coefficient is evaluated later on 7 heldout transitions without changing the already-running Paper original old-model forecast. Therefore distinguish **pre-Action frozen model / retrospective evaluation of future samples** from genuine per-tick MP9 Paper prequential FIXED events; those have NOT been introduced.
4. Independent postrun auditor checks both physical Worlds, old Paper 8/7 chronology, actual source state match, ticket values and source SHA, one original `MP9_SHADOW_SELECTION_FIXED` before first WAIT observation. Failure preserves all originals and stops without scientific/qualification claims. Two World run is at most an engineering DEV observation.

## Preregistered tests — no favorable-result selection

For NORMAL and ICE targets, compute MAE for selected material-model, always-normal-model, always-ice-model, Zero and Last, on the same 7 heldout transitions.

Primary **environment-specific route condition**: selected MAE must beat the *wrong-surface coefficient* by at least `0.001m` in **both** target Worlds, AND the average selected MAE across both must beat the *better of two global fixed coefficients* by at least `0.001m`. One condition failing means `CONDITION_SPECIFIC_TRANSFER_NOT_ESTABLISHED`. This is a fixed DEV diagnostic threshold, not statistical significance; a negative is a valid experiment.

Always report a deterministic same-information one-bit material→coefficient lookup as **mathematically equivalent**. Neither fixed-model win nor a positive routing gate demonstrates a unique L1 cognitive advantage. Report possible Last win/loss and actual physical motion separately. Any difference in seed/position/velocity or unavailable Paper source is `PAIR_INVALID`, not a successful model transfer.

## Acceptance ceiling

`MP9_TWO_WORLD_DEV_ONLY` if both actual original Worlds and source audits pass; next-world performance and negative controls shown without selective omission. `L0_UNCHANGED / MEMORY_ADMISSION_0 / CHEAP_EQUIVALENT / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. No main merge. No R/V promotion. A genuine SelfBody→L1 **runtime** read interface, policy impact, learning admission and real-world generality remain separate later stages.

---

## Stage 1 actual original Minecraft heldout pair — DEV PASS, routing margin FAIL

[Actions run #41282040300](https://github.com/rinsakamo/relay-self/actions/runs/41282040300) **SUCCESS**, execution HEAD `0c80064bb23ebab115e888376d662cb28e1f5c62`. New disposable World NORMAL 1 + ICE 1; one original S49 Action and S16 OUTCOME each, original Paper WAIT8 / original prior local Paper FIXED/SCORE7 each; Java/Node exits0; no intra-run retries. Full original ZIP artifact `mp9-two-world-originals-41282040300-1` ID `13074061185`, SHA256 `e0d62a458ffd7bcfbcdb652a7cea8814463b94f96a0105525ed06e7772637b42`; [independent source readback](evidence/issue653-mp9-surface-selector-20261101/run1/independent-physical-readback.json).

All 2 World initial Paper-sampled pose/velocity/health/food/ground comparisons matched, with independent new seed `114230270`; Paper lock fullTime NORMAL 291 and ICE 289, **not temporally identical**. NORMAL original MOVE `0.6269065734210613m`, ICE original MOVE `0.703745088643206m`. This **reversal versus MP8** confirms that the numerical size/direction of native movement contrast is not stable enough to infer a friction-only causal effect.

The exact MP8 prior was sealed before the first MP9 World; original Paper source material lock for each World preceded S49 Action; `MP9_SHADOW_SELECTION_FIXED` exact ticket appeared in host original prediction journal before the first WAIT sample. New MP9 selected coefficient was not emitted as seven independent Paper-internal FIXED events. We score those pre-Action frozen functions on the later verified actual 7 WAIT transitions (prospective model / retrospective target scoring, clearly distinct from the original Paper MP5 prequential sequence).

### 7-transition heldout MAE (m)

| Predictor | NORMAL | ICE | Pair mean |
|---|---:|---:|---:|
| Material-selected MP8 coefficient | **0.0031249586** | **0.0128973895** | **0.0080111741** |
| Always NORMAL coefficient | 0.0031249586 | 0.0134680349 | 0.0082964968 |
| Always ICE coefficient | 0.0034469819 | 0.0128973895 | 0.0081721857 |
| Last observation | 0.0070703126 | 0.0137771442 | 0.0104237284 |
| Zero | **0.0021077733** | 0.0374312081 | not used in pair benchmark |

The selected coefficient was directionally better than the wrong-surface coefficient **in each of these two Worlds**, but its margin was only `0.0003220232m` on NORMAL and `0.0005706454m` on ICE. The pair-mean improvement versus best global constant was only `0.0001610116m`. Therefore BOTH preregistered `0.001m` gates **FAIL**. This is a legitimate negative/weak result, not demonstrated environment-specific knowledge transfer. The deterministic cheap material lookup is **exactly equivalent** to the shadow selector; unique L1 advantage is absent. On NORMAL, Zero predicts better than the selected model.

Preflight: Python3.12 **75 PASS**, Java21 ice gate **15 PASS**, Ruff/contracts PASS, Maven BUILD SUCCESS, original assets SHA verified; original source audit and process cleanup PASS. Source of prior = MP8 heldout real pair (not World reuse). Original S49/L0 owner, L10/S10/S11, Goal, R/V unchanged.

**Final classification:** `MP9_DEV_TWO_NEW_MATCHED_PREACTION_WORLD_PASS / DIRECTIONAL_SURFACE_MAE_GAIN_SMALL / PREREGISTERED_SPECIFICITY_GATE_FAIL / SAME_INFO_CHEAP_EQUIVALENT / L1_UNIQUE_ADVANTAGE_NOT_PROVEN / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
