# Stage27a — Real Stage26 L1 READY → original owned Intent and Skill (DEV)

Parent: Cognitive Architecture #828, Skill IR/ActionPort #843; predecessor
Stage26 real 2-Self/Checkpoint/Gemma result Draft PR #929 and Issue #860.
This Stage27a change is intentionally **not** a physical-MOVE success claim.

## Reason this must be staged

The verified Stage26 Self A/B result is a real Gemma BOUNDED numbered
selection (A/B both choice `1`, `READY`) after restoration of the
operator-accepted MOVE Preset. It already proves model → original Self
decision. It does **not** prove the next physical step.

A literal handoff to the existing resident MOVE issuer is currently invalid:

- Stage26's selected Goal is `EXPLORE_WORLD`.
- Its Target is a **DESTINATION** with `TargetContract.kind=PLACE` at
  the fresh position plus 1m world-east, using an operator DEV template;
  the terrain and body orientation are not qualified.
- `PhysicalIssueAdmission.issue_move` ultimately uses the original
  `issue_selected_move_dev`, which accepts only `target_kind=RELATIVE`,
  `WALK_RELATIVE` and `relative:forward|back|left|right`.
- `FiniteSkillInterpreter.propose` explicitly refuses a
  parameterized `PhysicalSkillIR.invocation`, pending source-qualified
  constraints/budget enforcement.

**Never rewrite the original DESTINATION into a relative direction, or
silently discard the Preset/budget/Target.** A direct physical MOVE
would bypass the very L1-selected Invocation identity the experiment tests.

## What Stage27a adds

`begin_stage27_owned_move_intent` consumes the exact Stage26
`PreparedStage26L1`, `ResidentInferenceTicket`,
`RealGemmaChoiceWitness` and post-model native probe. It requires:

- Current A-only original `CheckpointedCognitiveOwner` and shared GPU
  work-owner scope, with the same native session and World epoch.
- Real bounded provider result `choice=1`, `READY` and unmodified
  request/response SHA256 source receipt.
- The same original registered Preset, immutable Invocation and
  TargetContract as selected for Stage26, healthy fresh native readback,
  and original resident issue session online.
- Empty original Intent/Skill, open Action supervisor and canonical WAL
  before any mutation, plus a valid owner/cohort mutation gate.

It calls the **original owner's** `commit_intent` and `start_skill`
exactly once; it does not allocate a parallel Intent owner, issue a
PhysicalActionPort proposal, mutate peer B, send Mineflayer commands, or
create an Action or WAL row.

The result `INTENT_STARTED_TARGET_RESOLUTION_REQUIRED` keeps the
original selected `invocation_ref`, `preset_ref` and current Self/native/
World identity. `target_resolution_attested`,
`physical_proposal_authorized` and `physical_action_issued` are all
false. This is a **pending Intent**, not a completed Skill.

## Next gates before any physical effect (Stage27b onward)

1. WorldBody provides a source-qualified, current native target resolver
   for `PLACE` navigation (orientation, obstacles, move affordance),
   not a fabricated `relative:forward` or operator-chosen angle.
2. L0 interprets the *same* selected, frozen `SkillInvocation`,
   retaining the immutable Goal/Target/constraints/budget identity.
3. Extend the **original** parametric physical issuer with a bounded,
   native-attested MOVE contract and enforced budget/duration/position
   fence; do not weaken `FiniteSkillInterpreter.propose` globally.
4. Reserve canonical WAL PREPARED, original native child-ID grants,
   ACK/effect/readback and terminal or unresolved classification.
5. One real isolated World DEV: A alone may receive the first physical
   Action; B's original Intent/Skill/WAL remain unchanged. No automatic
   replay or repeated World attempts on uncertain STOP/Outcome.
6. Only after physical Outcome is source-correlated may L1 evaluate,
   learn, or attempt another Goal/Intent cycle.

Stage27a tests use synthetic HTTP/native fixtures only; exact-HEAD CI
must pass before any local real-World test. Existing EULA and real-World
DEV approvals remain in force, but neither is a replacement for a
correct parameterized motor issuer. QUAL and SCIENCE are not claimed.
