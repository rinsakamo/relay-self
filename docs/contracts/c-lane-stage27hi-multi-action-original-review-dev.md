# C Lane DEV — Stage27h/i multi-Action terminal L0 → original bounded L1 → explicit C1

This integration-only branch extends the Stage27i + C Lane Stack #1029. The
original Stage27h loop executes 2–4 serial native PLACE MOVE Actions under
the existing PhysicalIssueAdmission leases, not through new C Lane authority.
Stage27g's review hardcodes exactly one Action and must not be reused on
multi-child WAL or interpreted as implicit Goal success.

## Original-source continuation

`src/relay_self/c_lane_stage27hi_multi_action_review_dev.py` supplies a
separate, bounded **read-only** review, using the existing original
`Stage27hBoundedMoveLoop` terminal state and its own
`_validate_owner_and_journal()`; it checks all original child Action IDs,
terminal outcomes, physical WAL schema-v2 SHA/ordered sequence, bound
`SkillInvocation`/Preset/TargetContract, WALK/SNEAK gait tags, and STOP
reservation clearance. It must have `L0_TARGET_REACHED_YIELD_EVALUATION` and
a CURRENT observed Target after the last physical child. It also verifies
the original `OwnedResidentPhysicalBridge` Owner and Paper World UUID,
branch, epoch and current native process. No caller-provided foreign World
label may qualify.

Only **after** terminal L0, a new `BoundedChoiceRequest` is submitted
through the **existing original shared one-slot resident GPU lane**.
Choices are CONTINUE, REVIEW_COMPLETION, ESCALATE_L2 and DEFER.
The payload includes the exact ordered original Action IDs, original WAL SHA,
Target, Preset, physical observation, gait modes and explicit false
Skill/Goal-success flags. The model's number 2 still does NOT mutate Self.

After the actual original provider returns with stop/token facts and raw
HTTP request/response SHA256, a **new native probe is required**, after
confirmed GPU idle. If the Target moved away, completion-review is downgraded
to non-adoptable. A separate original Owner adoption of this new CURRENT
WorldBody is required.

A second, explicit `OriginalSelfC1Approval` supplied by the actual cognitive
decision path is needed for `accept_stage27hi_original_c1`. Under the
original Owner's cognition lock, the complete L0/WAL/source and original
model result + raw HTTP bytes + new CURRENT probe/Target are rechecked.
It first builds the candidate C1 using a **detached prospective terminal
Skill snapshot** via existing `assemble_stage27_c1_from_canonical_wal`,
with all original ActionSupervisor OUTCOME children and first/last native
sources. Only after this preflight may the same original Owner
`finish_reviewed_skill`, `retain_memory`, and save/reload its canonical
`cognition.json`. No parent Intent/Goal completion, no new physical
authority, no Action replay or learned Skill installation is implied.

## DEV tests

The test runs the Stage27h original three-Action loop against its original
synthetic Mineflayer native and fsynced WAL; the review performs exactly one
additional owned L1 HTTP request against the **scripted** local provider.
Number 2 alone leaves the original Skill STARTED; a **synthetic** second
explicit acceptance terminalizes exactly one Skill and retains exactly one
C1. A typed original `SelfOwnerCut` writes and reads back the terminal Skill
in isolation. B, original Intent and physical WAL remain unchanged, and
duplicate adoption refuses.

Adversarial cases reject absent/foreign approval, foreign Action/Skill/World,
stale CURRENT probe, tampered raw provider HTTP SHA, original WAL changes,
cognitive Owner fence, non-review L1 choice, Target movement and edited
review frame. No fake model/principal permission is converted into a grant.

## Not attested

- The new test's native/Paper data and one-slot llama model are **synthetic**.
  No actual Gemma model or real Minecraft World ran.
- A caller-built `OriginalSelfC1Approval` is not proof that the actual
  autonomous Self made the decision; independent acceptance source is still
  required for real DEV.
- The Stage27h/i real launcher is not yet wired to call this module.
- This slice verifies one original typed SelfOwnerCut roundtrip, **not** a new
  same-source full World+A/B COMMITTED generation, not new Stage28 native/Paper
  rejoin and not a demonstrated L1 A/B learning advantage.
- After any IO/persistence failure, operator reconciliation is required;
  no original physical child is retried.

Classification:
`DEV_ORIGINAL_MULTI_ACTION_SYNTHETIC_REVIEW_CODE /
REAL_SELF_APPROVAL_NOT_ATTESTED / REAL_WORLD_LONGITUDINAL_NOT_RUN /
QUAL_NO_GO / SCIENCE_NOT_RUN`.
