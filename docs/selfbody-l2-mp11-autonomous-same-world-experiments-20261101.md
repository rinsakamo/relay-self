# RelaySelf MP11 — L2-driven experiment planning in ONE Minecraft World

2026-11-01; stacked on MP10 Draft #663, parent HEAD 0f3c6e1b18bb4b4630bfea5efe98412bd3e4a31e. Issues #653/#537.

## Intended capability

L1 detects a body-motion prediction mismatch. L2 (real Gemma via existing RelayEngine.open in future live deployment) proposes its own falsifiable explanation of possible model-structure or applicability failure, selects a **next** physical experiment and a prospective numerical motion prediction, examines the outcome, and independently selects what to test next **without World restart**. L0/S49 alone grants and executes actions. Original S16, S50, P1, M0, and SelfBody/World evidence ownership must remain intact. An operator-hardcoded A→B→C sequence alone does NOT satisfy autonomy.

MP10 demonstrated typed next-native epoch error reporting in two separate one-Action Worlds, but its single-coefficient OLS repair made effectively zero improvement. MP11 therefore permits phase-dependent, speed-dependent and surface-dependent hypotheses in addition to a single-slope model, without prematurely admitting a learned model.

## Stage 0 implemented — synthetic fixture, not physical proof

Module adapters/mineflayer/self_body_s50_l2_mp11_experiment.py:
- L2ExperimentLoop binds one World UUID, subject UUID, and session ID; up to four distinct safe condition labels, no repetitions and no outstanding simultaneous proposal.
- Calls the established RelayEngine OPEN request shape (real API); allows strictly typed JSON output with experiment_id, model_family, rationale, falsification_test and predicted_wait_total_m. No commands/code/action issuers permitted, no default scripted provider.
- Candidate conditions: GRASS_SHORT, ICE_SHORT, GRASS_LONG, ICE_LONG. Families SINGLE_DECAY, PHASE_DEPENDENT, SURFACE_DEPENDENT, INITIAL_SPEED_DEPENDENT, OTHER_BOUNDED. The chosen trial and predicted total Paper WAIT displacement are frozen before any future response.
- The following L2 call receives preceding trial prediction errors and history via source-labeled CognitionDatum, with unused experiment options, so a changing choice is possible. Model output is not World truth; old Paper window never becomes native Present.
- WorldTrialReceipt is **an unverified owner-supplied fixture**, not a real-world source. Its checks only constrain IDs/chronology/finite displacement/claimed floor and input regime. They do not independently authenticate original Paper stdout and native S16 source. Stage 0 cannot attest real input duration or floor changes.
- Test driver fake OPEN provider chooses four different experiments and hypotheses after reading feedback. A separate test drives actual RelayEngine.open through a fake provider. These are synthetic tests, NOT real LLM/Gemma calls, and they issue **zero** Minecraft Actions.
- Invalid/foreign material, repeated Action, stale/nonconsecutive tick, forged session/world/subject, invalid model output, surplus Minecraft command, nonfinite prediction and unavailable provider fail closed.
- Output ledger has zero persistent learning admissions and no L0 policy changes. Always retain a source-status flag distinguishing fixtures from real World originals.

## Stage 1 physical owner refactor — NOT IMPLEMENTED

Existing MP10 S49 host has ONE Action per World with one-shot S16/S50 lease, Paper marker, predictor and native source sealing. It cannot honestly execute 3–4 experiments in one World merely by looping the MP10 two-World runner. A physically valid same-World bridge must add:
1. One persistent real Paper 1.21.8 World and same Mineflayer/S49 session, a global resource/time/STOP budget and source-qualified health/food/fatigue safety. Only one outstanding original Action.
2. Independent bounded L2 OPEN model invocation with real backend credentials and recorded provider calls; no fake/CPU fallback counted as Gemma. L2 proposal freezes BEFORE the target experiment's original S49 Action.
3. Multiple original S49-issued and S16-closed separate Actions in the SAME World, distinct per-action Paper markers, each with eight real WAIT samples and full input/initial velocity/material audit. A verified SHORT/LONG control difference is required; labeling identical moves differently is not an experiment.
4. Same-World state reset/settling and verified sample condition; per-trial source binding to original Paper and Node bytes, no extra observer/Action owner, no unnoticed retry. L0 may reject any trial and interrupt L2. An invalid outcome is a retained negative result, not learning.
5. Separate model-fitting trials from prospectively frozen heldout trials. Compare last-value, global fixed, surface-lookup, and same-information simple phase/speed baselines. Never use fitted data to claim independent L2 generalization.

## Qualification gates

| Gate | Evidence | Status |
| --- | --- | --- |
| G0 | Four-round synthetic OPEN L2 feedback loop, model-schema and owner denials | IMPLEMENTED; verify CI |
| G1 | Actual Gemma L2 proposes and revises different experiments from new evidence | NOT RUN |
| G2 | One real persistent World, 3+ original S49 Actions and S16 OUTCOMEs, independent original readback | NOT IMPLEMENTED |
| G3 | Distinct source-verified conditions and 8 WAIT per trial, correct per-trial state resets | NOT RUN |
| G4 | Independent heldout model transfer and cheap baseline comparison | NOT RUN |

Acceptance ceiling: MP11_STAGE0_OFFLINE_L2_PLANNER_ONLY / REAL_L2_NOT_RUN / REAL_MULTITRIAL_WORLD_NOT_RUN / L0_UNCHANGED / NO_LEARNING_ADMISSION / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. Draft only; main untouched.
