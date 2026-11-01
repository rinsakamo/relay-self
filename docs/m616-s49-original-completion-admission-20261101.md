# M #616 — S49 original completion DEV admission (2026-11-01)

## Mission / owner separation

The user-confirmed original S49 owner [Draft PR #674](https://github.com/rinsakamo/relay-self/pull/674), exact HEAD `702f75c9fab3c42053ca0c89af670db1e306c892`, ran a disposable real Minecraft 1.21.8 World once and measured **WAIT→MOVE_AWAY→MOVE_AWAY**, original S16 OUTCOME ×2, matching native event/probe/request IDs and clear-controls. The verified original evidence is on **the user's local machine** at `/home/rinsa/work/s49-readback-evidence-20261101/run002/s49-report.json`, **not uploaded or copied** to this M branch/CI.

This M branch is **stacked on M #670** exact HEAD `c58cc4f41c5f839487d19d50841b344bd242eb0f`, not the S49 branch. Original S49 product is pinned read-only in test CI. No edits to S49's original S14/15/16 Action, S42 original coordinator, B0/P1, L8, learning, Gemma provider, any production runtime or main.

## What this M adapter admits

`experiments/metabolism_s49_owner_admission.py` is a dedicated S49 admission namespace **distinct from** S42 `SLMDevTapResult` and cognitive `CognitionCostSample`.

Two intentionally different inputs:

1. **`ORIGINAL_PYTHON_BATCH`:** `admit_original_s49_batch(batch)` requires an actual original typed `S49OriginalCompletedBatch` produced by S49 and re-runs the **original** `read_original_s49_completions` on the **same original** `L0Step`, Mineflayer probe and S16 receipt references. Verifies exact object identities, native source/order, grant and S16 outcome through S's own validator. This preserves process-local object identity but is **not** independent Paper/Minecraft source attestation.
2. **`SAVED_REPORT_JSON`:** `admit_saved_s49_report(report)` verifies original S49 report `status=PASS`, observer `CALLBACK_RETURNED`, zero-exit cleanup, original `S49_ORIGINAL_COMPLETION_DEV_V1` allowlisted row, corresponding three original decision/probe source traces, exact terminal/action association, and the original `verify_native_action_evidence` decoded-frame checker (before→dispatch→clear→after, position-derived horizontal displacement). It cannot recover Python object identity or independently authenticate a saved JSON file. Classification is **report-declared, internally consistent** only.

`S49MAdmissionLease` is default-OFF, handles at most eight bounded batches in one S49 session and rejects replay, source ID reuse, session change, or non-monotonic event order. Rejected/disabled results carry no admission, never silently retain partial success. All M diagnostics remain passive and contain **no native reads, LLM calls, Actions, B0 debit or learning writes**. Source is explicitly `source_attested=False`.

`bounded_s49_m_admission_row` exports only schema/session, WAIT/S16 counts, exact type distinction, **UNKNOWN** model/CPU/GPU/tokens/wall time, **UNKNOWN** B0 energy and L8 learning; never raw World snapshot, decoded frames, model text, personal data or Action authority. In particular, `provider_calls=None` is NOT measured 0. A DEV readback's `new_model_calls=0` means the **readback code** did not call the model; it is not a universal cognition consumption measurement.

## How to test actual saved S49 evidence (LocalCodex, offline)

On the user's machine, after checking the original evidence path and hashes, run in an **isolated M branch worktree** (working tree stays clean):

```bash
PYTHONPATH=src:. python -m tools.m616_s49_saved_report_check \
  --report /home/rinsa/work/s49-readback-evidence-20261101/run002/s49-report.json \
  --admit-dev
```

It prints one bounded `M_S49_ORIGINAL_COMPLETION_DEV_V1` status row and exits 0 only if the original saved report's internal consistency passes. It **does not** start Minecraft/Java/Node, contact any model, write evidence, or modify the original JSON. Keep stdout/stderr and return code in a fresh external evidence directory; save errors without replacing the source file.

**Important:** GitHub CI uses a *synthetic typed S49 S16 fixture and synthetic saved JSON assembled via the original S49 code*. The actual saved World JSON remains absent from CI; until LocalCodex runs the command, do **not** report that the real saved run002 was ingested by M.

## Tested scope and exclusions

New `tests/test_metabolism_s49_owner_admission.py` runs in the same process with **pinned immutable original S49 #674 owner** and asserts the source-owning Python module is from that checkout, while the M adapter is from the M branch. Tests positive typed and JSON paths, identity preservation, decoded S15/S16 evidence and many fail-closed negatives (unknown result, wrong source/Action/clear/sequence, false B0/L8/S42, foreign session, replay, default OFF).

Do **not** reinterpret original S49 `L0Step` as original S42 `DecisionEpochResult`; S49 has no qualifying B0 or L8 owner in this path. No `CognitiveWorkReceipt` is minted; real model resource metering remains unconnected and must be separately authorized/observed. Any claim of goal attainment, retained learning, L0 crystallization or cognitive efficiency requires further evidence.

Classification: `DEV_ONLY / OFFLINE_M_S49_ADMISSION / SAVED_REPORT_NOT_YET_RUN / S42_B0_L8_UNKNOWN / MODEL_USAGE_UNKNOWN / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
