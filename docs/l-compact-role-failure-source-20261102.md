# RelaySelf L — compact Gemma OPEN and failed-source visibility (2026-11-02)

Stacked child of Draft PR #679. Issues #431/#653.

## Historical result remains a FAIL

The previous new Paper World failed. One actual Gemma HTTP response was generated with 512 completion tokens and finish_reason=length. The canonical provider correctly rejected it: valid OPEN 0, H1 unadmitted, H2 not reached. Original S49 Action1 and S16 existed, but the whole-World result and both mandatory audits remained FAIL. The unadmitted response made three incorrect metric citations out of four and confused next-tick prediction with absolute error in free text. Never modify those historical originals, hashes, or verdicts to qualify the previous run.

## Three source-only changes

1. New l_mp11_compact_role_table.py produces an exact source-bound role/index table for completed Paper Action(s). Index 0 contains WAIT8_TOTAL_M and PAPER_CHEAP_NEXT_TICK_MAE_M aggregates. Index 1 through 7 identifies each distinct original forecast/absolute-error pair. The optional prior Gemma forecast/error targets the following trial WAIT8 TOTAL, trial 2/index 0, never a next-tick pair MAE. The model is told to copy exact original values; it cannot overwrite the independent numeric validator or learn a causal surface rule without different physical surfaces.
2. Existing L2 OPEN preserves the 512 max_tokens budget, strict finish_reason=length rejection, no retry, original HTTP journaling, strict JSON, and no Action/World learning authority. The instruction is shorter, explicitly names all ten output fields, requests one citation on the first call and at most two on the second, and asks for short falsifiable explanations. The parser enforces the matching citation limit; any incorrect reference is still rejected.
3. The original S49 physical completion record is appended immediately after an authentic S16 outcome, before Paper WAIT and the L2 OPEN. A post-cleanup partial source summary is produced even if a later model OPEN fails: native Action/S16 counts, prior Paper prefix count, model attempted/validated counts, raw Paper SHA and recognized EOF shape. It is explicitly nonqualifying and cannot cause either mandatory audit or the World to pass. Missing or noncanonical Paper originals remain errors, not repaired source.

## Verification and next physical milestone

Dedicated Python3.12 offline CI tests the explicit role table, prompt/role scope, known failure chronology, error-source-only provenance, fake Gemma JSON rejection, old S49/G2/G3/Paper and typed feedback regression. No new Minecraft World or genuine Gemma inference is executed in this increment.

Next local physical DEV must predeclare one disposable Paper World and the exact execution HEAD before the run, independently verify model file/llama process, then run at most three original S49 Actions and two actual Gemma OPEN calls with no retry. Archive all original HTTP/Paper/W3 data on either success or failure. Qualify only when the mandatory independent original audits both succeed; evaluate A=valid live OPEN and B1=previous-hypothesis feedback separately from B2=model performance improvement and C=autonomous physical experiment.

Status: COMPACT_ROLE_AND_FAILURE_OFFLINE_ONLY / HISTORICAL_WORLD_FAIL_UNCHANGED / NO_NEW_WORLD / NO_NEW_REAL_GEMMA / NO_L0_PROMOTION / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
