# Cognitive v0.1 — shared physical DEV issuer envelope (#843, #849)

## Scope and exact baseline

This is a **refactor** stacked on #848 at
`b6409cfb271fa09ffb97ffe8f3ee5ab283a3c379`, whose controlled
Minecraft/Gemma ATTACK was reported `REAL_L0_ATTACK_HURT_PASS`.
#847 at `87d81cbf0fe9226641244a06bab0d6e7a972c161` reported
`REAL_L0_EAT_PASS`. **Neither physical result qualifies the refactored
branch:** it requires a fresh real-World DEV regression before any
`REAL_COMMON_EXECUTOR_PASS` claim.

## Single Self authority, no hidden re-planning

The same IntentCommitment, SkillExecution, ActionSupervisor,
`propose_bound_physical_action` and Self-owned PhysicalActionJournal
remain in place. The CPU L0 cursor requests one bound Action; neither
the common issuer nor WorldBody capability code selects Goal, Skill or
Target. There is **no** new second owner, native process, prompt, operator
credential or autonomous background retry.

`experiments/cognitive_physical_executor_dev.py` factors the
**shared guarded physical execution envelope** out of the EAT and ATTACK
capability-specific DEV issuers:

1. Reject invalid CLI grants/owner, non-typed transient proposal, stopped
   Mineflayer process, bad host timing or timeout. Check durable
   `journal.require_clear()` **before** acting on a potentially stale
   in-memory proposal.
2. Verify exact source-bound two-probe `PROPOSED` ActionPort receipt:
   correct native session, request IDs, seq, owner, Action ID,
   Skill/Capability version and target kind. The caller then checks its
   specific food or entity facts; this common check is not World safety.
3. Validate two distinct scoped PROPOSE/ISSUE caller labels, rejecting
   stale/mismatched target, owner or request. They are **DEV labels, not
   authenticated physical operator principals**.
4. Verify current committed Intent, STARTED Skill, no reconsideration or
   competing supervised Action; preserve chosen Capability identity,
   World session, Self owner and fresh native source. Historical same-World
   source-reuse is rejected by the existing journal.
5. Authorize the existing proposal and persist the original shared WAL
   `PREPARED_UNRESOLVED` with lock/CAS/file+directory fsync before
   original ActionSupervisor.ISSUED or any Mineflayer command. The
   dispatch is **closed to EAT@1 and ATTACK@1**. The common executor
   never issues native effects by itself.
6. The existing EAT issuer performs `equip_item → consume_held`, checks
   applied ACK and Food/inventory consequence. ATTACK performs one
   `attack_entity`, checks applied ACK + source-attributed
   `entity_hurt` and after-probe. Those checks **remain capability-specific**.
7. The shared terminal helper records the original ActionSupervisor
   OUTCOME, invokes the capability's exact WAL close validator, then
   `require_clear()`. Any exception from native issuance/evidence/close
   retains the durable unresolved journal; if the in-memory Action
   is still ISSUED it becomes UNKNOWN. If the WAL close fails after
   an in-memory OUTCOME, durable `PREPARED_UNRESOLVED` still takes
   precedence on restore; never replay.

Compatibility: `PhysicalEatGrant` and `PhysicalGrantStage` stay
available from their historical EAT module as import aliases for existing
DEV tools. These labels are not real authentication.

## Invariants and exclusions

- Exactly one Self journal; original v1 EAT and ATTACK row schemas and
  fsync/CAS verification remain the canonical physical history.
- No new `ActionLifecycle`, `SkillExecution` or Intent authority.
- Physical OUTCOME is **not** Skill SUCCESS nor Intent ACHIEVED. L0
  returns only terminal candidate.
- ACK is not proof of damage. ATTACK's native `entity_hurt` still lacks
  independently joined Paper UUID/entity ID/event/tick/delta evidence.
- `source_entity_id=null` or any uncertain effect is not a success.
- Runtime still lacks authenticated grants, cross-process body exclusivity,
  a persistent L0 cursor, durable intermediate raw event/PROPOSED evidence,
  generalized MOVE/REST and post-hoc semantic Skill evaluation.
- The common helper deliberately dispatches only known EAT/ATTACK
  capabilities and their existing native issuer methods. Arbitrary
  model-generated capability names or Python callbacks are **not** accepted
  by the issue stage.

## Tests and acceptance

Offline regression tests explicitly cover grants, foreign/stale native
source, capability swap rejection, WAL-before-ISSUE, nonissuing gate,
persistent UNKNOWN on restart, successful Food-based terminal closure,
and all prior EAT/ATTACK happy-path and ambiguous native-effect cases.
Run complete repository pytest, lint, contracts and Mineflayer adapter CI
on the **exact refactored HEAD**. Then LocalCodex should independently
exercise controlled real Gemma/Minecraft EAT and ATTACK DEV on this new
HEAD without resetting any unresolved Self journal. Do not upgrade
qualifications from offline tests alone.

Classification until that test:
**OFFLINE_DEV_ONLY / REAL_COMMON_EXECUTOR_NOT_RUN /
QUAL_NO_GO / SCIENCE_NOT_RUN**.
