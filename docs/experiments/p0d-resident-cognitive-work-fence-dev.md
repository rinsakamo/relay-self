# P0-D Stage 20 — Self-scoped cognitive writes / CPU-task retirement (DEV)

Stacked Draft #894 onto #892 (original physical issuer), #889 (World resident lifetime), #885 (all-N global checkpoint) and #880. This is an **opt-in alternative to the global cohort gate**, not a second cognitive owner or a change to full-world rollback rules. Neither autonomous real Minecraft play nor QUAL/SCIENCE is authorized.

## Original owner connected

The original `CheckpointedCognitiveOwner` now forwards a Self identity when checking cognition mutation authority. `CognitionOwnerCohort` accepts the optional identity without behavior changes to the existing global gate. `ResidentCognitiveWorkOwner` attaches the same existing original owner objects to **one indexed per-Self gate** instead of the global cohort. Each actor uses the original `retain_memory`, `commit_intent`, `start_skill`, `accept_pattern` and session/tick observation methods with one shared reentrant lock; a quarantined/offline actor cannot mutate any of those originals, but peers can.

On source-qualified login, the existing Stage19 `OwnedResidentPhysicalBridge` binds the fresh native session and actual observed World clock to the original cognition object. On logout, the original physical issuer is revoked **first**, then cognition admission closes synchronously before any await. The coordinator cancels all registered **actual asyncio CPU task handles**, waits up to a bounded timeout for every handle's termination, and checks that no new work appeared. Only after the original native process, WAL and persistent cognition have also been checked can that actor become OFFLINE.

An asyncio cancellation REQUEST is not counted as a task STOP: if the coroutine catches cancellation and does not terminate within the bound, the actor stays QUARANTINED, cannot install a late memory result, and cannot be recognized as retired for World-only save. Other actors remain fully writable and retain their original physical issuer leases.

**Result origin:** A completed CPU work task does not mutate Self memory by itself. The new `commit_memory_from_work` explicitly checks Self ID, Task ID, original native session, **Self work epoch**, World epoch, task completion and non-exceptional result before calling the original `CheckpointedCognitiveOwner.retain_memory`. Old tokens are unusable after logout or subsequent login, even for the same Self.

## Local peer work, not external transport

`stage_unsent_peer_message` tracks messages which have explicitly **not left the Python owner**. On retirement these pending messages become in-memory `LocalPeerDiscard` tombstones with `externally_sent=False` and `recipient_delivery_authorized=False`. They cannot automatically reappear or be delivered to another Self as a side effect of restoration. This is **not** a real inter-Self channel, durable message protocol, delivery acknowledgment, replay or causal history join. External sends remain categorically forbidden by Stage19 `InertResidentWorkBoundary`.

## GPU and LLM limitations

The current repo has no common production L1/L2 backend task owner that can prove actual model generation STOP and GPU/VRAM release per Self. The Stage19 inert guard remains in place and **forbids GPU task registration**, leaving attempts permanently unqualified. Stopping a Python asyncio Task is NOT proof that a llama.cpp HTTP inference request stopped in the backend, GPU memory was freed, or another server's task was cancelled. No L1/L2 GPU task was run here.

This DEV stage does not claim cancellation or draining of processes/threads outside this explicitly scoped owner. The original direct EAT/ATTACK issuer call sites remain to be audited for complete physical issue coverage. Existing `CheckpointedCognitiveOwner` mutable values must not be written directly by unqualified external references, and direct native effects still require the canonical `PhysicalIssueAdmission` final-stdin hook.

## Verification and next qualification

Offline N=2/10/100 tests with real Python original cognition-owner fields, persisted memory, original physical issuer/WAL, **owned OS process mimicking Paper**, and typed synthetic native streams cover:
- one Self CPU task cancellation and complete task STOP while N−1 Self continue cognition mutations and guarded EAT
- stale work results rejected before and after re-login, identity/retained memory preserved
- local unsent peer message discarded without delivery or claimed sender/receiver effect
- deliberately cancellation-resistant CPU task timing out; only affected actor HOLDS, later clean retirement after actual coroutine STOP
- original World-only archive after all per-Self physical+cognitive retirement; no Self snapshot or old Action replay

Exact final HEAD / five CI job results are reported in Draft #894 and Issues #860/#851/#828. Real backend GPU resource-owner integration, source-qualified GPU STOP/VRAM readback, external peer delivery/log ownership, actual Paper world play and live cross-World switch remain **NOT ATTESTED**. Status `RESIDENT_COGNITIVE_CPU_OWNER_OFFLINE_DEV_PASS` only if exact-head tests PASS; `LIVE_L1_L2_GPU_RETIREMENT_NOT_ATTESTED / REAL_PEER_TRANSPORT_NOT_ATTESTED / REAL_PAPER_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
