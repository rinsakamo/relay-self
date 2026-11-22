# C Lane DEV — Stage27g post-Action review → explicit original Self Skill/C1 adoption

This branch builds on original Stage27i + C Lane #1003. It does not alter
Stage27 #990's original physical issuer, Stage28 #988's real checkpoint runner,
or any real Paper World. All new tests use the existing synthetic HTTP/native
Stage27 fixtures, **not actual Gemma/Paper**.

## Existing gap

Original Stage27g is **read-only**. It obtains one bounded L1 number (2 =
`REVIEW_COMPLETION`), waits for a new native probe, checks the original target
still qualifies, then explicitly leaves `SkillState.STARTED`. The number is
not itself an autonomous Self success/Memory adoption decision. The Stage27h/i
multi-Action loop does not automatically run Stage27g post-action review at
all. Stage27's current real runner's COMMITTED generation is pre-action.

## New split boundary

- `prepare_original_stage27g_c1_review(...)` is read-only. It rechecks the
  original resident A owner and current World/native slot, original model
  ticket/result and **actual raw request/response SHA256 bytes**, resolved
  number-2 completion recommendation, bound original Invocation/Target,
  exact original canonical terminal WAL, current original Action and Skill,
  post-model native current observation and fresh geometric Target assessment.
  It returns a proposal, never a success or an Action grant.
- An **independent explicit Self decision** must supply
  `OriginalSelfC1Approval` with
  `ACCEPT_SKILL_SUCCESS_AND_RETAIN_C1`. Constructing a matching dataclass
  is **not** authenticating the decision. A future original cognitive path
  must independently establish that Self actually accepted it; tests use an
  explicitly synthetic external approval.
- `accept_original_stage27g_c1_review(...)` rechecks all sources under the
  original cognitive-work-owner lock. Before modifying any original owner
  state, it computes a **detached prospective terminal Skill** and uses the
  existing Stage27 C1 source bridge to validate the WAL, original before/
  settled native observations and Target outcome; duplicate Memory holds.
  It then calls the existing `CheckpointedCognitiveOwner`'s new gated
  `finish_reviewed_skill` API, calls **that same original Owner**'s
  `retain_memory`, atomically saves/readbacks its existing canonical
  `PersistentCognition` file, and rechecks original WAL SHA. The parent
  Intent is left active and no Goal success is credited. No second owner,
  model POST, physical issue, skill replay, automatic retry or C2 is added.
- Failure during persistence is HOLD; no automatic reissue/rollback of a
  possibly terminal physical Action. The Skill and Memory must be reconciled
  by a separate original owner/Checkpoint source audit, not guessed.

## Scope and limitations

The first vertical slice covers **one original Stage27g terminal MOVE_PLACE
Action with a real-shaped bounded review**; Stage27h/i's 1–4 Action loop
needs its own post-loop outcome review and pre-stop integration (not silently
passing it through Stage27g's one-Action exact-WAL gate). The actual operator
real World runner is **not** modified in this branch; there is no real C1
commit or real Stage28 post-action typed World+A/B cut yet.

Tests use Stage27g's own resident inference lane + scripted HTTP and native
sources; verify that a returned number 2 alone does not mutate Skill or
Memory, that separate *synthetic* explicit approval can commit exactly one
original bounded C1, leave peer B / Intent / WAL unchanged, and reject source,
session, stale CURRENT, deferred approval, changed model HTTP bytes and
duplicates.

For real continuity, the next integration must use operator-verified
Stage27g raw source + independently evidenced explicit original Self
approval, then **new post-action** original World+A/B typed COMMITTED Stage28
cut, and independent Paper/native rejoin for the **same World UUID**.
A model recommendation cannot independently prove a Self approval.

**Classification:** DEV_ORIGINAL_OWNER_SYNTHETIC_REVIEW_CODE /
REAL_SELF_APPROVAL_NOT_ATTESTED / REAL_WORLD_C1_NOT_ATTESTED /
QUAL_NO_GO / SCIENCE_NOT_RUN.
