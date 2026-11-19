# C Lane C1 — Original Stage27 / Stage28 read-only bridge (DEV)

**Status:** inter-Draft integration seam. Stage27/28 are unmerged, and the underlying real physical World was **not** loaded. Tests are deterministic mock-source compatibility checks, not proof of real WAL authentication or Stage28 rejoin. No actual Memory adoption or new Action. This PR stacks on C Lane Draft #993; base #993 stacks on #840 → #838 → #836 → #834 → #832 → #830.

## Reuse-first exact branch audit (2026-11-19)

- Original Stage27 source: [Draft #990](https://github.com/rinsakamo/relay-self/pull/990) HEAD `02449bbcf786f73ba41737fd60e792174b65fd94`, stacked on #979. `src/relay_self/physical_action_journal.py` owns canonical `PhysicalActionJournal.restore` with original SHA256 envelope, lock + digest verification and readback. `src/relay_self/target_contract.py` owns source-bound `evaluate_target`; the same source does **not** prove Goal achievement.
- Original Stage28 source: [Draft #988](https://github.com/rinsakamo/relay-self/pull/988) HEAD `a8be2f7a01cdef80678307a350c5a721789745b2`. `CheckpointedCognitiveOwner` has `retained: PersistentCognition`, `native_session_id`, `current_worldbody_observation`, and owner-only `retain_memory` admission after fresh rejoin. Two-Self full current-session rejoin is not assumed proved.
- Current C branch **does not vendor these unmerged physical/checkpoint modules**. Runtime integration imports explicitly **HOLD** if original modules are unavailable. Repeated import/pseudo fixtures are not treated as original World proof.

## Adapter flow

```text
Existing L1 selected SkillInvocation (immutable Goal/Target/Preset)
      + original IntentCommitment, terminal bounded child SkillExecution
      + original ActionLifecycle[] + native before/after probes
      + Stage27 original physical Action WAL path and exact SHA256
    -> PhysicalActionJournal.restore (original checksum/record admission)
    -> verify all original MOVE_PLACE rows: source session/seq/Intent/
       SkillExecution/Action/Invocation/Preset/TargetContract
    -> re-evaluate existing TargetContract from final native position
       (Target condition, NOT Goal success)
    -> re-read original WAL with same SHA to fence concurrent writer
    -> existing C1 BoundedSkillRead/Experience
    -> propose_for_stage28_original_owner (only after independently
       verified original cohort + new native rejoin; previous World UUID)
    -> existing native Memory proposal, no write; Self may accept separately
```

## Meaningful gates

- `SkillExecution.STARTED` or WAL `PREPARED_UNRESOLVED` => HOLD. Current Stage27h/27i can leave Skill STARTED pending owner L1 evaluation; **the original Skill owner must terminalize it independently**, not this C bridge. Do not synthesize terminal by reading a geometrical Target condition.
- Scope, child Action IDs and exact original SHA256, native source session and monotonically increasing seq, first/last native probe identities, positions, original invocations, Goal/Target/Preset and contract refs must match. Original WAL restore rejects checksum, ACK chronology, STOP settling, unrecognized status. Retained C1 readout is separate from this physical origin validation.
- `evaluate_target` may return `CONDITION_OBSERVED`, `OUTSIDE`, `UNKNOWN`; C1 Target assessment maps to SUCCESS/PARTIAL/UNKNOWN **only for observed Target condition**. No Goal/Intent/Skill success is newly committed.
- Native fulltime = Minecraft day/time; **not** the Paper process-local TickWitness that Stage28 uses. No cross-domain tick comparison is made with Paper. Same-Session monotonic native readback only.
- Restored Stage28 owner is an independent later world/native session. Recovered Self identity, verified World UUID supplied by Stage28, cohort membership, latest actual native probe, old-session invalidation (different session), and fresh-observation fence must agree. Stage28's independent generation/World files/Paper presence attestation are **upstream responsibilities**; C's `verified_world_id` argument is not independently authenticated.
- Stage28 admission returns a `Memory` value **without calling** `owner.retain_memory`. Revision/CAS, duplicate recognition, checkpoint persistence and explicit adoption still belong to the original Owner. No memory is silently grafted into another Self or epoch.
- Original `PhysicalActionJournal.restore` takes its own lock and may create an original `.lock` file; the bridge itself does not write the journal body or issue Actions.

## Tests and remaining integration

Offline tests use the actual C `IntentCommitment`, `SkillExecution`, `ActionLifecycle`, `PersistentCognition` and synthetic **mock** external Stage27/28 modules. They check one bounded child, multiple original Actions, active child HOLD, PREPARED HOLD, digest mismatch, foreign source, native/Target mismatch, UNKNOWN target, recovered Owner Memory proposal without mutation, and stale rejoin rejection.

To qualify the actual World:
1. Materialize Stage27 #990 and C #993 together in a **separate**, explicit integration worktree/stack without touching their owners; evaluate real original WAL, native probe and independently verified Target assessment. Account for the fact that current Stage27 Skill may not terminate; HOLD if so.
2. Materialize Stage28 #988 and perform its *existing* independent World/cohort verification before testing C's historical Memory proposal. Do not treat World-only snapshot as 2-Self verified.
3. Owner-selected adoption (single owner/revision, durable checkpoint after readback), then B vs A next epoch L1 bounded-choice evaluation with original current cue. No pre-bound L1 parameters altered.
4. Only after real independent evidence may DEV real-World source qualification be claimed; QUAL/SCIENCE remain separate.

**Classification:** DEV cross-Draft adapter + synthetic contract tests only. No actual Stage27/28 integration proof, QUAL NO-GO, SCIENCE NOT RUN.
