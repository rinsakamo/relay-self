# Stage28a — one typed World + two Self owner recovery admission (offline DEV)

Parent [#966](https://github.com/rinsakamo/relay-self/issues/966). This Draft is stacked on the
Stage24g source HEAD `230e1ee90f9932480a60dad9990124990d532341`.
Stage27 PLACE work is independent and is **not** part of this branch.

## Source result and scope

Stage24g independently attested one real Gemma numbered choice MOVE and
native/Paper movement correlation (1.723147m) plus a **World-only** checkpoint.
Its archive `world-only-000000000000`, declared tick 290, contains **zero
Self owner snapshots**. Its 305-entry original evidence manifest
`b79646397ecf67f3b0c840964dfc7ee4fe669f2347cab264c9c303131c6716f1`
remains immutable. Stage24f still HOLD. World-only progress cannot be
retroactively converted into a World+Self recovery proof.

This slice reuses original `capture_typed_generation` /
`verify_typed_generation` / `restore_generation` /
`staged_recover_cognition_cohort` as the **only** admissible cognitive
restore source. It does not implement a competing checkpoint or physical
issuer.

`stage28_inert_cognitive_recovery` requires:
- the **exact same committed generation** for World + every Self in a fixed
  unique roster, with valid original Intent/Skill/Preset/Memory envelopes,
  cross-Self delivery receipts, canonical physical WALs and source World ID;
- no Self observed tick **later** than that generation's stopped World tick;
  earlier Self snapshots may be stale and must be reevaluated, not replayed;
- a new branch fork with correct `RESTORE_PREPARED.json` and source receipts;
- independent SHA256 and exact inventory readbacks on **all** restored World
  and Paper companion dimension files, in addition to the archive's existing
  checksum verification;
- all recovered Self candidates inert, fresh WorldBody required,
  no old Skill resume, old L1 decision reuse, old peer redelivery, or
  automatic physical Action issue.

Matching a cognitive snapshot C98 to a separately saved W100 or W110
solely by tick is **insufficient**. The action and peer state at those
intermediate times cannot be inferred from tick order alone. This gate
refuses synthetic merging of generations. A later C105 cannot join
W100; W110 does not become a valid mate without an actual joint cut.

`stage28_require_fresh_l1_eligibility` validates *separate* original
`NativeLoginEvidence` receipts for each Self: a new World branch and Paper
session, new native sessions distinct from both old and each other,
fresh observed tick, invalidation of old sessions, clear physical WAL,
fenced stale GPU and peer work, authentic new-source probe claims, and one
exclusive idle slot. Its only positive output is **eligibility to
reevaluate L1 via the existing owner/provider**. It does not invoke the
model, grant a physical Action, or imply Goal completion.

These Python receipts alone are **not** independent proof of a real
Minecraft session. Real Paper/native/llama provenance must be separately
attested by their original owners before these functions can contribute
to an integrated DEV result.

## Next work

28b: wire the existing `CoordinatedCheckpointHost`, neutral STOP and
original `PhysicalIssueAdmission`/native owner to a new real A+B Paper
typed checkpoint (all dimensions, 60-second autosave, whole-cohort
COMMITTED marker). A qualified full typed World+Self cut is indispensable.

28c: restore a new branch, verify exact snapshots and old WAL, fresh
Paper A/B join with new sessions and Body probes, then call the existing
real Gemma L1 *again* to make a **new** choice. Do not replay the old
MOVE/Intent or prior GPU output. Follow with an original Native/Paper
Outcome only if that new L1 choice actually issues an Action.

## Classification

`STAGE28A_OFFLINE_RECOVERY_CONTRACT_ONLY / REAL_TYPED_WORLD_SELF_CUT_NOT_RUN /
FRESH_REAL_L1_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
Stage24g DEV success, Stage24f HOLD and all their original evidence remain
separate and unchanged.
