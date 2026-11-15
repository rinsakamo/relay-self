# P0-D #860 — Stage 17 N-Self bounded full-roster barrier (DEV)

Stacked on Stage 16 #880 and its native/physical/cognitive source gates.
**This stage is synthetic and does not make real Paper, QUAL or SCIENCE claims.**

## What is generalized

- STOP: existing same `PhysicalIssueAdmission.begin_neutralization` closes
  all normal effect leases **before** any asynchronous native STOP. Bounded
  workers (operator opt-in `stop_parallel_workers`, default 1, max 64)
  process every distinct current Self in parallel. Each keeps its own
  exclusive fsynced PREPARED/VERIFIED STOP receipt and 8+8 tick test.
  Complete, ordered, distinct roster and `neutralization_complete` are
  required before any cognition or World save. Cancellation or timeout
  aborts the one shared physical epoch and leaves WAL reconciliation
  for the operator. Maximum entire STOP phase: 60 seconds.
- Freeze: bounded threads (`freeze_workers`, default 1, max 64) execute
  the existing typed per-Self owner `freeze_and_flush` hooks. All workers
  are joined before Paper can save/stop. The actual
  `CognitionOwnerCohort.freeze` takes a coherent immutable owner cut
  and checks the physical WAL under its coarse RLock, then releases
  that lock for **independent per-Self fsynced IO**. Rebind/release reject
  active, failed or incomplete generation freezes. Injected delayed-write
  tests prove overlap of independent file writes under one globally closed
  checkpoint gate; failed owner IO prohibits a World save.
  The owning cohort refuses aliasing/nested canonical per-Self roots and
  uses an indexed Self-ID lookup instead of a linear scan.
- Rejoin: `CoordinatedAutosaveRuntime.run_if_due_async` now prepares
  native sessions via a bounded async group (`rejoin_parallel_workers`,
  default 1, max 64), with 15-second per-Self and 180-second total
  timeout defaults. Rejoin workers **never** rotate the physical owner;
  the barrier validates all source IDs and uniqueness before invoking
  canonical synchronous cognition rebind. Stage 16's source-qualified
  WorldBody readbacks still happen inside the closed gate before
  any global physical release.
- Initial native source probes can be opted into the same bounded fan-out
  via `initial_probe_workers`.
- Membership is **fixed for each generation**, not a live
  auto-enrollment protocol. No split/partial COMMIT, quorum success,
  resume of missing agents, replay, asynchronous/split-brain release or
  new independent ActionPort.

A static set of N registered Self remains one failure domain: one actor
missing, with unresolved STOP, a failed flush, unresponsive native
launch, duplicated new native ID or stale probe HOLDS the entire cohort.
No claimed 60-second scheduling SLA. Disk copy/hashing is still
O(World bytes + total Self checkpoint bytes), and reboots remain
full-world and full-cohort. Stop worker count and actual Paper tick
rate/bandwidth must be tuned independently from model inference.

## CI evidence and next gates

N=2,10,100 synthetic native tests exercise the **actual existing**
CheckpointedCognitiveOwner/PersistentCognition/Intent/Skill/WAL owners,
typed N-Self generation manifests, full all-or-nothing STOP/rejoin and
two scheduled 60s generations. Fault injection covers missing last Self,
wrong request ID in STOP, last native rejoin timeout/error, duplicate
new session IDs, and one failed freeze callback, actual concurrent owner IO, and a
  simulated fsync failure. The synthetic World
uses an in-process `WorldRuntimeHooks` fake; there is no real Paper,
Mineflayer, network, native GPU task cancellation, or physical delay
benchmark in these tests. CI result and HEAD must be attached after run.

Further qualification must add actual 3/10/100 native process stress
in a disposable isolated Paper environment, plugin/world Save ACK,
source-qualified timing, multi-world roster adaptation, disk IO limits,
actual GPU scheduler retirement, plus strict crash/rollback tests.
