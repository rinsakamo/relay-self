# Cognitive v0.1 — causal World/Self checkpoint reconstruction

Issue #851; parent #828; Common I/O #829; epistemic boundary #833; physical WAL #843. The branch extends #850 HEAD e676ec68d4627df85a1474ccebfa1d34b40f00c5.

**Status: OFFLINE MODEL ONLY / no real Minecraft World restore / no physical Action issue / QUAL_NO_GO / SCIENCE_NOT_RUN.**

## Core example and distinction

W110 may contain a dead Zombie UUID Z1. Self A C105 remembers attacking it, while Self B C98 remembers Z1 alive. C98 and C105 do not have to be simultaneous. However, W110's dead entity alone cannot prove that A killed it. Another Self or the environment may have caused the state, or the client entity ID could refer to another UUID.

Two kinds of consistency must remain separate:

- **Physical history consistency:** World branch, checkpoint validity, Action owner and ID, self-owned WAL, actual world event and independent actor/target/tick join. Missing joins are HOLD, not inferred passes.
- **Epistemic consistency:** each Self may remember OBSERVED, INFERRED, PREDICTED, or erroneous claims from a past moment. Such beliefs stay source/tick scoped, not enforced on current World or silently deleted.

## Read-only v0.1 contract

The new module src/relay_self/causal_recovery.py contains typed:
WorldCheckpoint, WorldEntityState, SelfCheckpoint, ActionClaim, BeliefRecord,
SentMessage, ReceivedMessage, WalReceipt, WorldEvent, RecoveryDecision.

WorldCheckpoint includes world_id, branch_id, checkpoint_id, monotonic logical tick, claimed atomic capture, claimed effect-event coverage and limited World entity states. **The attestation and coverage fields are not cryptographic verifications.** Minecraft daytime does not define a stable monotonic causal tick; tick origins and branches must be tracked externally. Saving region/entity/player/POI state needs a coordinated World capture; a save command alone is not an atomic transaction with Self WAL, in-flight TCP or JVM queues.

SelfCheckpoint contains per-Self partial cognitive history, not a global truth DB. A Self checkpoint may be older than the World checkpoint. A Self newer than the restored World is held for cross-branch reconciliation, not silently treated as World truth.

WalReceipt is a read-only projection of the existing Self-owned PhysicalActionJournal after independent restore. Existing WAL schema, lock/CAS/fsync and unresolved restart STOP are unchanged. Terminal WAL status is not an independent server-side effect; PREPARED_UNRESOLVED blocks.

WorldEvent represents *one joined World-effect summary per parent Action* (not native EAT child commands) with world/branch, actor Self ID, Action ID, previous native session, original native Target ref, server-side target UUID, server tick and two source refs. Its raw source join is externally supplied, not authenticated here. Missing native Entity ID → UUID/tick join blocks physical resumption.

The pure gate assess_reconstruction returns:

| Verdict | Meaning |
|---|---|
| REJECT_CHECKPOINT | Mixed/torn World capture, branch mismatch, contradictory physical final state |
| HOLD_PHYSICAL_RECONCILIATION | Future cognition, unresolved or absent WAL, missing causal World event, unmatched UUID/actor/session, cross-Self missing send, event coverage gap |
| CANDIDATE_REOBSERVE | No known typed physical contradiction; fresh native/Schema observation and separate owner fencing still mandatory |

Every verdict reports **action_issue_authorized = False**. A candidate never grants replay, restores the L0 program counter, issues a native Action or changes a Goal or Intent.

If historical evidence shows a Self's belief was wrong, the evaluator emits an epistemic review warning; it does not reject a coherent physical checkpoint or overwrite memories.

## Test cases

Synthetic tests cover A C105/B C98/W110, W100 rollback while A C105 remains, same tick on a new branch, torn World backup, mismatched UUID, runtime entity ID relabel, missing/unresolved WAL, action attributed to the wrong Self, missing native/server causal linkage, missing cross-Self sender event, absent effect coverage, external actor, distinct respawned Zombie UUID, erroneous historical belief, duplicated Action ID, and 128 independent ON/OFF fault combinations.

This is a **logic/contract test**, not evidence that real Minecraft 1.21.8 can atomically save and replay JVM/World state or source-join Paper UUID/native events.

## Real integration still open

1. **World checkpoint adapter:** reliable offline save manifest for Minecraft world, server generation/branch token and monotonic event sequence with content hashes and no mixed chunk/player/entity save generations.
2. **Independent event recorder:** source-join Action ID + native session + native runtime entity ID to server UUID/tick/health and raw event refs; preserve unknown if impossible. Do not reinterpret #848 HURT_PASS as independently measured DAMAGE_PASS.
3. **Existing cognition owners:** persist current Goal/Intent/Skill lifecycle and accepted Recent/Retained references with branch/source stamps through their existing authorities, not via a new central planner or truth store.
4. **Restore gate:** compare saved World capture and all participating Self-owned WALs; quarantine future-branch memory, keep unresolved physical effects blocked, reconcile messages and verify cross-process issuer fencing.
5. **Present rebuild:** after preflight, reobserve WorldBody through qualified Percept → Schema CURRENT, reproject present with source-scoped RECENT/RETRIEVED, reconsider Intent, and rebind all runtime entity references.

Resume only after separate native currentness, capability, owner and journal grants; this module by design never creates such grants.
