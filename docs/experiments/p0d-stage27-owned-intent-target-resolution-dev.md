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


## Stage27b — Read-only original PLACE-to-WorldBody geometry (offline)

Implementation `src/relay_self/p0d_stage27b_place_motion_dev.py`;
contract tests `tests/test_p0d_stage27b_place_motion_dev.py`.
The resolver takes the **Stage27a original owned Intent receipt**, the
original Stage26 immutable complete `SkillInvocation`, the original
`CheckpointedCognitiveOwner` and `PhysicalIssueAdmission`, and one
source-scoped **fresh native probe**, and produces `Stage27PlaceMotionPlan`.

Required bindings: same Self ID/native session/World epoch; exact
request/invocation/preset/TargetContract refs; live original Intent and
STARTED Skill; original WAL still clear, no active Action; native probe
not older than the Stage27a post-model recheck. No new L1 or L2 model
request is made. Peer B's Intent/Skill/WAL are untouched.

`evaluate_target` reuses the original immutable PLACE arrival envelope:
the Stage26 DEV example is 1 metre world-east of the initial body,
arrival within 0.6m, so the initial native x-position has a 0.4m
**gap to envelope**, but is not itself an arrival certification.
`mineflayer_yaw_to_target(position, target)` converts only the native
body position and original target anchor into the Mineflayer-native
expected yaw; for positive X the result is `-pi/2`. **This is a desired
angle, not observation that the body is facing that angle**. The current
native snapshot lacks current yaw/pitch or navigability/obstacle proof.

The plan's `clearance_observed`, `facing_aligned_observed`,
`action_granted`, `native_effect_issued`, and
`world_goal_succeeded` remain **false**. No `send_look`,
`send_set_control`, `send_clear_controls` or WAL call occurs here.

Budget is the *frozen original Preset*; this stage exposes
`preset_max_distance_m` and whether it can geometrically finish the
envelope. If target distance exceeds that cap, it is **not** proof the
Self cannot make progress; the future physical issuer may attempt
a smaller bounded movement, then report the actual Body Outcome.
The Preset may not be silently increased or rebound by L1.
An observed obstacle/failed movement is valuable Body feedback, not
a priori evidence that the Target/Goal should disappear.

**Not implemented and still essential for Stage27c physical test:**
- original resident `PhysicalIssueAdmission` MOVE family only permits
  native `set_control` and `clear_controls`, and its durable MOVE WAL
  requires `relative:* target_ref` plus start/stop child IDs
- parameterized PLACE `SkillInvocation` cannot pass the current
  `FiniteSkillInterpreter.propose` admission. Do **not** bypass it by
  replacing the selected PLACE Target with a synthetic RELATIVE target
- to issue a native LOOK and bounded forward MOVE safely, the owner
  must explicitly extend its native child lease and durable WAL
  identity for the original `TargetContract` and Invocation; record
  native ACKs and final STOP settling/readback, enforce the per-Preset
  duration/actions/distance caps and final source-correlated Outcome
- all results (including no displacement/blocked) must be attributed
  to the exact original Self/Target/physical parent and treated as
  feedback; automatic retries on uncertain STOP are forbidden

No real Stage27b Paper/real Gemma/physical MOVE trial has been run by
this branch. Source-shaped tests are synthetic. Stage26's verified
real-world classification remains separate.
