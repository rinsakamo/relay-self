# M #616 — S49 actual Action/S16 original owner receipt join (2026-11-02)

## Why this source boundary

The already verified [S49→M live DEV result in #676](https://github.com/rinsakamo/relay-self/pull/676#issuecomment-6566429277) read the complete original `S49OriginalCompletedBatch` in the same process: original L0 `WAIT→MOVE_AWAY→MOVE_AWAY`, original Action/S16 OUTCOME ×2, native S15 clear and real Minecraft movement. It was **not** a live S42/B0/L8 complete-owner epoch.

Source audit of pinned original S49 owner `702f75c9fab3c42053ca0c89af670db1e306c892` finds `_native_epoch_two(...)` inside `s49_normal_session_real_ci.qualify.on_action`, but its local `epoch` and S14 `values` are **not exported** through the S49 post-completion `completed_l0(batch)` callback. The existing callback exports only original returned S49 `L0Step`, original Mineflayer decision probe, and original completed S16 `NormalActionReceipt`. The actual B0 owner `B0EnergyLedger.decide` and the L8 owner's `LearningEpochResult` do **not** run in that S49 callback.

Therefore it would be incorrect to declare real S42/B0/L8 receipt supply, or to cast an S49 L0Step into S42 `DecisionEpochResult`. A proper additional owner-provided S42/B0/L8 callback requires a separately reviewed owner-side interface: **M must not manufacture them.**

## New source-bound M receipt readout

This isolated M branch stacks on #676 exact `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`, without edits to S49 product, S42/B0/L8, action issuer or main.

- `experiments/metabolism_s49_original_owner_receipts.py` provides a **default OFF**, single typed callback read `observe_original_s49_s16_receipts` requiring both **the original S49 typed batch** and the already RECORDED exact-source `S49MAdmissionReadout(kind="ORIGINAL_PYTHON_BATCH")`. It re-checks original typed S49 owner readback, exact step/probe/S16 receipt Python references and M source binding; any mismatch results in **atomic DEFERRED**, with no partial receipts or Action authority.
- For each MOVE, the original S49's **`capture_native_action_evidence` verifier** checks the original S16 `before→dispatch applied→S15 clear applied→after` frame provenance, native identity and independently recomputed movement from decoded position. S49 decision probe is strictly earlier than S16 before frame; the next decision event must occur after the preceding S16 after frame.
- The only retained *live in-memory* `S49MOriginalActionReceipt` contains original Python references, Action ID, event/probe/receipt sequences and measured source displacement. Its **bounded output** does not expose any original source object, World snapshot, inventory, health or raw provider text. `provider_calls/input_tokens/output_tokens/wall_ns/cpu_ns/gpu_ns=null` are preserved as UNKNOWN; no B0 energy or L8 learning is measured.
- `s42_owner_receipt`, `b0_owner_receipt`, `l8_owner_receipt` are always `NOT_SUPPLIED_BY_ORIGINAL_S49_COMPLETION_CALLBACK`. They are **not placeholders which M may fill**; adding real owner fields later requires a separate, source-bound owner contract.
- `tools/m616_s49_live_owner_dev.py` now adds `m_original_s16_receipts` to the separate bounded M report. Overall M `RECORDED` additionally requires per-Action source receipts to agree with original S49 saved Action IDs/event/probe/movement and the independent typed admission. M remains post-owner, read-only and never issues Action, probes, LLM calls, food or learning writes.
- `tests/test_metabolism_s49_owner_admission.py` changes only the **synthetic fixture** to model the real-world condition that S49 decision probe and S16-before are different native observations. `tests/test_metabolism_s49_original_owner_receipts.py` adds direct original object identity, native frame ordering/clear/movement proof, WAIT, default-OFF, replay and failed/forged owner negatives. All CI tests use pinned original S49 checkout, **not a new World**.

## Next real DEV check (LocalCodex)

After exact-HEAD CI green, in an isolated M worktree, run the **same** grant-gated `tools.m616_s49_live_owner_dev` against a *new disposable World*, saving separate S49 and M JSON reports. The user has given continuing RelaySelf DEV World authorization; no repeated per-run permission request is necessary for this scope. Record **every** World and pre-world failure, preserve original evidence/previous run data, and check:
- original S49 `WAIT→MOVE_AWAY→MOVE_AWAY`, original S16 OUTCOME ×2, two S15 clears, no open Action;
- M `ORIGINAL_PYTHON_BATCH / RECORDED`, new `m_original_s16_receipts.status=RECORDED` and per-Action before/dispatch/clear/after sequences matching S49 saved original Action evidence;
- S42/B0/L8 `NOT_SUPPLIED`, cost UNKNOWN, source_attested false, M Action/native/model/learning/energy side effects zero;
- Java/Node exit0, cleanup/port release and pinned code/previous evidence unchanged.

Do not report **actual new World success** from this offline CI. If the original S49 owner cannot expose additional S42/B0/L8 receipts, classify them as absent until an owner-controlled extension is separately developed and verified.

Classification until new real World: `DEV_ONLY / S49_S16_ORIGINAL_RECEIPT_JOIN_OFFLINE / S42_B0_L8_NOT_SUPPLIED / SOURCE_UNATTESTED / REAL_WORLD_NOT_RERUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
