# RelaySelf L — source-exact evidence IDs for prospective real Gemma OPEN (DEV)

2026-11-02. Child of L Draft #680 (after #679). Issues #431/#653. **No new actual Gemma or Minecraft World is run in this change.** Historic #679 original World FAIL and its two mandatory audit FAILs remain unchanged.

## Problem

The previous actual local Gemma request ended at 512 completion tokens with finish_reason=length (valid OPEN0). Its not-admitted candidate had only 1/4 numerically correct references, confused single-pair forecast with error, and never produced a real H1/H2 loop. Shortening output and giving an explicit numeric role table (#680) was an improvement in input design, but still required a language model to copy multi-decimal numeric fields and pair numbers back into JSON.

## New opt-in translation contract

Explicit runtime gate: CLI --l-mp11-evidence-ids-dev, with L_MP11_EVIDENCE_IDS_DEV=1, requires the existing real localhost L2 engine and original completed live Paper prefix mode. Default OFF. Legacy numeric_evidence_refs mode remains unchanged, including its test/failure classification.

The new model-facing request retains all the existing prior-only original Action/S16/Paper context and frozen previous L2 hypothesis + typed feedback. Its auxiliary source catalog lists typed original evidence IDs, roles, indexes and numeric values, and the model returns exactly ten JSON fields with an evidence_ids list instead of numeric_evidence_refs. Only 1 ID is accepted for H1 and at most 2 for H2. Examples:
- T1_W8 → original trial1 WAIT8_TOTAL_M, index 0.
- T1_CMAE → original trial1 CHEAP next-tick MAE, index 0. This is not the WAIT8-total prediction error.
- T1_P1PRED / T1_P1ERR → trial1 first frozen next-tick prediction / its absolute error, index 1.
- T2_H1PRED / T2_H1ERR → previous L2 NEXT-WAIT8-total forecast / its absolute error, trial2 index0, only available after original trial2 is completed and H1 had a nonnull forecast.

A candidate JSON with an unknown/future/duplicate/unsorted ID, extra executable fields, more than 1 H1 / 2 H2 IDs, or mismatched H1 source/clock/context is denied. When valid, the host deterministically resolves the chosen ID against the **original typed source**, fills the corresponding exact numeric citation, records the selected IDs on the proposal and includes them in the immutable proposal hash. This does NOT silently correct old responses, does NOT entitle the model to an Action, and does NOT certify that the model understood the physical significance of its chosen ID. Choosing T1_CMAE while describing WAIT8-total error can still be a semantic mistake; no claim of effective B1/B2 revision from ID validity alone.

The existing canonical llama.cpp provider with max_tokens=512 and strict rejection of finish_reason=length is unchanged. Original raw HTTP request/response and freeze-before-next-Action behavior stay unchanged; a single malformed response causes fail-closed, no retry and no new Action. The original S49 executor remains the sole issuer. The independent audit_feedback_originals now reconstructs **the opt-in mode** from original report, recomputes prior-only request, raw model text, typed ID values and immutable proposal SHA, rejecting fake future Paper prefixes. Mandatory full original G3 and live-prefix audits remain independent gatekeepers.

## Evidence ceiling

GitHub CI for this PR uses synthetic Paper fixtures and fake provider outputs only, explicitly not the user's GGUF. It validates catalog source scope, ID resolution and rejection, exact prior proposal H1→H2 binding, independent source-readback, old numeric mode regressions, S49/G2/G3 owner contracts, Ruff/compileall/repository contracts. A fake provider labelled "llama.cpp" in a test proves parsing only; real model weights identity requires independent local process mapping + GGUF SHA.

No physical experiment condition was controlled or selected by L2 in this increment. No model training, learned L1 admission, permanent world schema, or L0 promotion.

## Next original physical DEV gate — only on local authorized WSL host

Confirm target Draft/head and preflight branch/worktree clean. Use a dedicated child worktree for physical DEV and a NEW evidence root; preserve #677/#679 failed originals. Verify the actual Gemma GGUF SHA, llama.cpp server process/weight mmap, source-built Paper Minecraft 1.21.8 plugin, server ports, VRAM headroom, and the baseline physical World grant. Predeclare **before start**:
- S49_REAL_SERVER_CI=1, MP11_S49_THREE_ACTION_DEV=1, MP11_G3_PAPER_THREE_WINDOWS_DEV=1
- L_MP11_LIVE_PREFIX_DEV=1, L_MP11_LIVE_L2_DEV=1, L_MP11_PAPER_EOF_DEV=1
- L_MP11_EVIDENCE_IDS_DEV=1
- S49 original CLI --mp11-three-actions-dev --l-mp11-live-prefix-dev --l-mp11-paper-eof-dev --l-mp11-evidence-ids-dev, plus exact localhost llama.cpp endpoint/model, pinned G3 original assets, original raw stdout and a new report path.

One disposable actual Paper World, one Mineflayer subject, at most 3 original S49 Actions and 2 actual Gemma OPEN calls. No retry/extra Action, no L2-controlled physical condition variation and no learning admission. Preserve both success and failure original raw and partial native/S16/Paper EOF witnesses. If the server gives finish_reason=length, reject as before; record token counts, original bytes and exact failed boundary. Do not use the new ID translator retroactively on the earlier truncated JSON.

For any candidate SUCCESS, independently run full G3 (--expected-live-l2-calls 2), live-prefix original readback, and L2-feedback independent original readback. The last must recompute exact opt-in evidence ID resolution, prior-only request, H1/H2 raw model output and SHA. Report A=valid live OPEN, B1=previous hypothesis evaluated using correct signed/absolute target and semantic reasoning, B2=verified different physical condition model update, C=autonomous condition choice separately. B2/C not achievable in the current unchanged-grass 3-Action World.

Classification for this PR: EVIDENCE_ID_SOURCE_DEV_OFFLINE_ONLY / REAL_NEW_WORLD_0 / REAL_NEW_GEMMA_0 / HISTORICAL_FAIL_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
