# S49 original completed L0/S16 passive readback (S owner; 2026-11-01)

Base: `self/product-self-one-command-selfbody-20261018` exact `087fe095a87594505392262da1d341cf0c65b2b2` (original S49 owner). This S-only change does **not** edit the M #670 or S #672 branches, the Action executor, B0/Energy, L8/Learning, original S42 coordinator or main.

## Why source-side rather than another simulated S42

Original S49 `qualify()` receives the genuine Mineflayer probe BEFORE decision through `live_probe`, but its `NormalWorldL0.run_session` returns **`L0Step`** after decisions. It does *not* return a complete S42 `DecisionEpochResult`, original B0 decision, or L8 snapshot. Creating a second S42 coordinator after the fact and calling that original S49 is invalid.

This first live-owner readback is deliberately a different source-bound type: `S49OriginalCompletedBatch`. Its `steps` retain exact original S49 `L0Step` references, original `MineflayerObservation` references stored in S49's existing `probes` dictionary, and for MOVE only exact original `NormalActionReceipt` stored AFTER S16 OUTCOME. WAIT has **no Action receipt**. Session, monotonically increasing event/probe sequences, request IDs, zombie entity and terminal Action IDs are checked. Missing/mismatched/replayed sources and unresolved S16 cannot be marked completed.

A batch has `real_s42_epoch_supplied=False`, `real_b0_decision_supplied=False`, `real_l8_epoch_supplied=False`, `source_attested=False`. It does not create a `SLMDevTapResult` or `CognitiveWorkReceipt`. Existing S #672 `SPostEpochL2OpenRuntime.execute` must **not** accept this as an S42 decision or infer an L2 call. This is real S49-owner **type identity**, not independent W3/Paper physical-source qualification.

## Product call-site / owner controls

- The original `s49_normal_session_real_ci.qualify` has optional `completed_l0` callback default None. The only call site is **after** the original `NormalWorldL0.run_session` returns three decisions, after S16 OUTCOME checks for original MOVEs, and after optional Stage R source checks. Failures in optional readback are caught and recorded as `OBSERVER_ERROR` without vetoing original Action completion or creating any more Action/native/LLM calls.
- Optional **CLI DEV** switch `--completed-l0-dev` additionally requires `S49_COMPLETED_L0_DEV_ONLY=1`, plus existing `S49_REAL_SERVER_CI=1`. It publishes `original_completion_readback` with only allowlisted session/event/probe/decision/action-id/terminal metadata in the existing S49 report. Default OFF has no added report field and does not collect receipts.
- Example only in an **authorized disposable S49 DEV World**, after checking the original server/JVM/Node resource preconditions:

```bash
PYTHONPATH=.:tests S49_REAL_SERVER_CI=1 S49_COMPLETED_L0_DEV_ONLY=1 \
python -m adapters.mineflayer.s49_normal_session_real_ci \
  --report /absolute/fresh/s49-report.json \
  --server-log /absolute/fresh/s49-server.log \
  --completed-l0-dev
```

The original S49 runner may fetch/provision its original disposable Mojang server, spawn Java/Node and consume a World. **Do not invoke this command in offline CI.** Ensure DEV authorization and source custody separately. In this work GitHub CI does NOT run it.

## Tested vs untested

`tests/test_s49_completed_decision_bridge.py` exercises the genuine original `NormalWorldL0.decide` with the pinned original S42 near/far native *fixtures*; its MOVE S16 receipt is an explicitly **synthetic typed** terminal/physical-effect fixture. Valid original-shaped MOVE/WAIT, object identity preservation, missing/foreign/replayed probes, swapped or UNKNOWN S16 terminal, and report export are covered. This does not prove native Minecraft movement or an actual World run. The real product call-site and default-OFF/CLI signatures are checked without opening server/LLM.

**Not yet achieved:** any new real World S49 readback, real Gemma L2 request, real S42/B0/L8 source handoff, M model-cost ledger, multi-epoch knowledge retention, or learning-related resource savings. Do not fabricate B0/L8/World source to satisfy M's old S42-only tap. S owner may next add a proper S49-specific receipt to the M source adapter under separate owner review; that is *not* evidence of S42. No Action authority, new native observation, model call, memory update, metabolic debit or habit grant is added here.

Status: `DEV_ONLY / OFFLINE_TYPED_S49_L0_AND_SYNTHETIC_S16_TEST / LIVE_HOOK_DEFAULT_OFF / SOURCE_UNATTESTED / REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
