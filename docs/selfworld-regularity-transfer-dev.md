# SelfWorld: compressed regularity and transfer — isolated DEV candidate

**State:** SOURCE_STAGED / PYTHON3_12_UNVERIFIED / NO WORLD / NO SCIENCE.
**Authority:** SelfWorld #633, S integration #537, Adaptive Cognition #426, S18 #354, stacked Draft PR #634.

## Revised conceptual target

SelfWorld is an **observer-local, fallible, compressed account of "what this world is like"**: structures and temporal regularities learned from experience, used to predict conditions in yet-unseen places. A Present snapshot or an indiscriminate dump of remembered observations is **not** itself such an abstraction. Prediction != observation; candidate pattern != verified universal law.

This new target **does not replace** existing SelfWorld v0's source-separated one-epoch view. Existing Memory remains the durable owner; PRD handles bounded projection; BLF and S17/S10 retain their separate evidence and write-authority contracts. No global truth, WorldModel database, second executor or independent semantic owner is introduced.

## Why stage a deliberately small candidate first?

2026-10-24 local Gemma-4-12B Q4_K_M matched A/B at PR #634 showed:
- Saved genuine W4 empty-probe source: no-context rubric 8/8, with SelfWorld context 0/8; all 8 measured pairs worsened.
- Synthetic four-case BOUNDED: no-context 16/32, SelfWorld 20/32; improvement and degradation mixed.
- No established UNKNOWN-withholding improvement. More context is not automatically more useful.

Therefore, the next question is **whether an inferred regularity gives novel-state predictive value relative to an inexpensive baseline**, not whether presenting more source JSON improves language model scores.

## Implemented candidate surface (isolated branch, not yet accepted)

The new experiments/self_world_regularity_transfer.py only:

1. Reads two-or-more explicitly supplied pairs of existing typed SelfWorldView / WorldObservation.
2. Validates same-Self, same-session, source-kind and session:seq provenance, monotonic bounded native sequence, positive exterior entity label at both ends.
3. Requires two distinct observed entities and two spatial regions (16-block X/Z buckets, an offline test feature, not certified terrain/chunk ontology), and denies duplicate source refs. One contradiction, unknown/partial pair or stale source prevents induction.
4. Compresses examples into **one immutable label-persistence candidate**, with label, bounded gap, region IDs, entity IDs and exact source refs. No raw observation copy or retained write.
5. Projects candidate through existing TransitionRule / PredictionState / predict_transition in PRD. An unseen-region holdout is MATCH/MISMATCH/UNDETERMINED. Missing subsequent observation is UNKNOWN, never absence or success.
6. Compares the same holdout against the explicit cheap repeat-last-positive-label baseline. **This prototype is expected to tie this baseline**. A tie is not a SelfWorld value gain.

The source and tests are synthetic/development inputs only. Historical W4 0/0 observations provide **no training positives**, so they cannot demonstrate acquisition. The mineflayer provenance string is not independent native source attestation. Heldout evaluation is retrospective and does not prove the prediction was issued before observing.

## Required local verification before adoption

- Exact starting HEAD and branch, tracked clean; no changes to protected 82 files, 770 historical index, Passive Views, S18 freeze or W4 saved sources.
- Python 3.12 focused tests for this candidate plus SelfWorld, PRD, source-bound replay, L0/Action-owner and S18 negatives; Ruff / contracts; Node22 where needed. Repair isolated DEV failures and rerun at final HEAD.
- Changed paths limited to the three new experiment/test/doc files. No extra PR, CI/FULL, Minecraft, physical Action/OUTCOME, Memory/S10 write or science.
- Explicitly report source forgery/replay, cross-Self leak, missing/contradictory evidence, location reuse and cheap-baseline tie.
- PR #634 stays Draft and unchanged pending an owner-approved fast-forward gate. S #545, main and historical originals stay fixed.

## Prospective useful SelfWorld gate (NOT solved by this prototype)

Later DEV: issue at least one genuine prospective prediction **before** the holdout observation, on a previously unvisited region, using a pattern trained on disjoint past sources. Match cheap observation-only/L0-L1 vs compressed-rule arms with identical source, action options and cost limits; include changed-rule/distribution-shift and UNKNOWN. Measure actual later actions/outcomes and independent token/latency/Body costs. Without net value over cheap mechanisms classify REGULARITY_VALUE_NOT_DEMONSTRATED and do not activate the new rule at runtime.

**Intended result:** bounded falsifiable candidate and evidence lineage, not proof of World laws or generalized cognition.
