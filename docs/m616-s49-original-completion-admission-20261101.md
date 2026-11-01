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

## Increment: pinned standalone CLI and original S49 live callback runner

The first real saved S49 run002 JSON was **successfully admitted by LocalCodex** before this increment (the user reported `RECORDED / SAVED_REPORT_JSON / exit 0`; original SHA256 `49a1280163d121486abf0c43d1af7af2c61efbf7531c1a1c603cfa699adf6716`; saved bytes unchanged). This initial CLI required a manual sys.path bootstrap because the S49 verifier module was not visible from the isolated M worktree. **This increment fixes the import path, but does not re-run that local file.**

### Offline CLI, now without a manual bootstrap

The M CLI explicitly loads the clean **original S49 #674 owner checkout** at exact SHA `702f75c9fab3c42053ca0c89af670db1e306c892`, checks its actual git HEAD/clean tracked tree and its owner module paths, then uses the original S49 verifier. If unavailable, it returns `DEFERRED`; it does not auto-fallback to M's older S49/S42 copy or synthesize evidence.

Example from a separate M #676 worktree (adjust owner path to actual clean worktree; no new checkout is created by the CLI):

```bash
PYTHONPATH=src:. python -m tools.m616_s49_saved_report_check \
  --s49-owner-dir /home/rinsa/work/relay-self-s49-readback-20261101 \
  --report /home/rinsa/work/s49-readback-evidence-20261101/run002/s49-report.json \
  --admit-dev
```

Default OFF and explicit owner path required. Never touches original JSON on disk. The pinned original S49 module's decoded S15/S16 verifier runs in the same process as M.

### Live S49→M DEV runner (requires an independent disposable World grant)

`tools/m616_s49_live_owner_dev.py` calls the **already existing original S49** `qualify(..., completed_l0=owner_tap, completed_l0_dev=True)`. It is *not* installed in the S49 product or its Action executor. M's `M616OriginalS49CompletedTap` receives the **same original completed Python `S49OriginalCompletedBatch`** after original L0 `run_session`, S15 controls clear and S16 terminal closure. It invokes `S49MAdmissionLease(enabled=True, max_batches=1).admit_batch(batch)`, stores only a bounded M audit row and discards Python source objects. The original S49 Action selection and issuer remain wholly unchanged.

The M wrapper reports `RECORDED` **only if** S49's final saved report is `PASS`, S49 reports `CALLBACK_RETURNED`, the synchronous M typed admission accepted exactly one batch, and the S49 session / WAIT / OUTCOME counts match M. Otherwise M reports `DEFERRED` even if a transient in-memory readback happened. A failure in M cannot veto, replay or replace S49's physical Action, and M status remains a **DEV original-source handoff**, not independent source attestation.

**This starts a new original disposable Minecraft World**, and requires an explicit new approved DEV World grant before using it. The authorization gates `--live-world-dev`, `M616_S49_LIVE_DEV_ONLY=1`, `S49_REAL_SERVER_CI=1`, and `S49_COMPLETED_L0_DEV_ONLY=1` must ALL be present. Also `NODE_OPTIONS` must be unset. The M runner checks fresh distinct S report, server log and M report destinations **before** contacting S49/Java/Node. The M report is an additional immutable `open("x")` file and does not modify the original S49 report.

Example **only after LocalCodex confirms grant**:

```bash
M616_S49_LIVE_DEV_ONLY=1 S49_REAL_SERVER_CI=1 \
S49_COMPLETED_L0_DEV_ONLY=1 PYTHONPATH=src:. \
python -m tools.m616_s49_live_owner_dev \
  --s49-owner-dir /home/rinsa/work/relay-self-s49-readback-20261101 \
  --report /absolute/fresh/s49-report.json \
  --server-log /absolute/fresh/s49-server.log \
  --m-report /absolute/fresh/m-admission.json \
  --live-world-dev
```

The live runner carries **no new native probes, Action grants/issuers, L2 calls, B0 energy debits, L8 learning writes, S42 synthesis or cognition meter**. Existing S49 original Action issuance is still physically real and remains subject to its separate grant/cleanup. `provider_calls=None` and other model-cost values stay UNKNOWN; no cost is claimed.

### Test scope and remaining step

CI tests both CLI entrypoints with non-world negative controls, the real original S49 typed protocol and M callback contract with a **fake qualify coroutine** and fixture S16, plus process-isolated actual canonical pinned-verifier CLI on a synthetic saved JSON. That is **offline**; a fake qualify callback is NOT a real Minecraft/S49 run. LocalCodex must confirm the standalone real run002 CLI still succeeds after the fix and separately perform a new-world DEV grant-controlled run to establish actual live callback identity. Do not conflate the two.

Classification until real live run: `DEV_ONLY / PINNED_CLI_AND_LIVE_CALLBACK_OFFLINE_TEST / REAL_LIVE_CALLBACK_NOT_RUN / REAL_MODEL_USAGE_UNKNOWN / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
