# P0-D #860 — Stage 19: Original Physical Issuer per-Self isolation (DEV)

Stack: Stage 19 → #889 World-resident lifecycle → #885 N-Self
coordinated generation → #880 native/work fences. **No merge, no QUAL.**

## Selected everyday model

The World is authoritative and may tick while one of N Self is
QUARANTINED/OFFLINE. A Self failure is first a **local physical
capability revoke**, not proof an already issued physical effect did
not occur. Old beliefs remain historical, and foreign-target events
are never silently replayed. Peers may act only under their own
original Action lease and current native session.

## Original issuer, not a new grant

The existing `PhysicalIssueAdmission` supports opt-in
`resident_mode=True, initially_offline=True`. Legacy full-cohort
checkpoint defaults stay unchanged.

- `quarantine_resident` atomically denies this Self's new EAT/ATTACK
  leases and its actual final native stdin effect callback. It leaves
  all peer sessions and leases intact. It records any in-flight
  Action; **quarantine is not terminal outcome or WAL clearance**.
- `retire_resident` requires the same token, old session and zero
  original active leases. It restores and validates the original
  fsynced `PhysicalActionJournal`, rejecting
  `PREPARED_UNRESOLVED` and missing/corrupt WAL. A failed retirement
  remains scoped to that resident.
- `admit_resident_login` changes only one old→fresh native binding
  after the same original WAL clears, the actor was safely OFFLINE,
  and an external source/World epoch check completed. The old child
  cannot regain issue privilege. It makes no new ActionPort.
- The existing full-N `close`/`begin_neutralization` refuse mixed
  online/offline resident sets rather than claim a global STOP.

## Owned process bridge

`OwnedResidentPhysicalBridge` connects the **existing** original
issuer to `WorldResidentLifecycle`, `OwnedPaperWorld`,
`CheckpointedCognitiveOwner` and original WAL. It uses the same
spawn + request-ID-correlated native probe as `OwnedNativeRejoinCohort`
and the real `MineflayerProcessSession.launch` API by default. A
strict localhost 1.21.8 config, a fresh running native process,
installed final effect admission callback, matching actual owned
Paper session, new native World tick, clean original WAL/Action
supervisor and a no-external-work boundary are required before the
original issuer admits this Self. Merely setting ONLINE does not
grant Action permission.

Logout revokes the original issuer **before any await**, ensures the
native owned child terminates, writes the original retained cognition
snapshot and reads it back, checks original WAL and then calls the
existing lifecycle's `finish_logout`. On failure the actor stays
QUARANTINED while peers keep their status/leases.

`world_only_quiescence` can supply Stage 18's original-issuer
retirement receipt only after **all** Self have individually completed
a bounded original-issuer/native/WAL/cognition logout. The World-only
archive stays a World-only generation; no Self cognitive snapshot is
fabricated, and no old action is replayed.

## Strict DEV-only scope and tests

The new `InertResidentWorkBoundary` refuses ANY GPU/LLM task or peer
message submitted through this owner, irreversibly tainting that
Self. It does not inspect foreign processes, external GPU/KV caches,
or other peer queues. The actual live L1/L2 resource scheduler and
communication owner are **not connected**. This is only a read-only /
no-external-work experiment; it MUST NOT certify real autonomous
multi-Self issue or cancellation.

The original `CheckpointedCognitiveOwner` values are required to be
unbound from the coarse global `CognitionOwnerCohort`; full autonomous
per-Self cognitive cancellation/snapshot and concurrent mutation
control remain future work. The original direct legacy native
issuers can bypass this issuer until migrated. The native probe is
not authenticated against Paper process identity from Mineflayer
TCP alone.

Offline N=2/10/100 test scenarios use actual Python original issue
leases, existing canonical WAL CAS and cognition persistence, an
owned OS subprocess **pretending** to be Paper console, and synthetic
native typed observations. They verify one logout with N-1 other
issuers continuing, fresh re-login vs stale native callback, failure
with active original Action, original **true PREPARED_UNRESOLVED EAT**
WAL refusing retirement, missing/corrupt WAL, bad native probe,
GPU-scope taint, and World-only save with an original scoped
retirement receipt. They are not real Minecraft or GPU evidence.

Classification after exact HEAD CI:
`RESIDENT_ORIGINAL_ISSUER_OFFLINE_DEV_PASS /
LIVE_PER_SELF_LOGOUT_NOT_ATTESTED / REAL_WORLD_ONLY_NOT_ATTESTED /
REAL_WORLD_SWAP_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.
