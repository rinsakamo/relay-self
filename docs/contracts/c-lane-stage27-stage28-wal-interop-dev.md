# C Lane DEV — Stage27 MOVE_PLACE canonical WAL ↔ Stage28 typed World/A+B cut

**Integration-only branch — no original owner code changed** in Stage27 #990, Stage28 #988, or prior C drafts #1003/#1009. No real World/Gemma and no physical effect issued.

## Reason for integration
The independent branch comparison showed that Stage27's **schema-v2 MOVE_PLACE** WAL and typed SkillInvocation/TargetContract are **absent** on Stage28's working lineage. Merely retaining a C1 Memory in Stage28 #1009 does not demonstrate that Stage28 can read/retain the original Stage27 WAL byte format.

The integration test branch overlays **exact** source files from Stage27i HEAD `02449bbcf786f73ba41737fd60e792174b65fd94` onto the tested Stage28+C HEAD `94129bb1b7feb6543eb17620010de52817e51a1d`:
- `src/relay_self/physical_action_journal.py` (additive schema v2, preserves schema v1)
- `src/relay_self/skill_invocation.py`
- `src/relay_self/target_contract.py`
- `src/relay_self/p0d_stage27b_place_motion_dev.py` (unmodified original source dependency; no real issuer invoked)

Stage28 also contains a newer **NATIVE_MOVE_NO_NET_DISPLACEMENT** terminal outcome for original relative MOVE that Stage27's WAL file did not include. The integration-only WAL reconciles that explicit terminal behavior into Stage27's additive v2 implementation; zero displacement still does **not** count as a successful move. Both source branches remain unmodified.\n\nThe overlay is **not a recommended merge plan**: Stage27/Stage28 production owners must reconcile their shared WAL module and test migration before merging; do not resolve their branch differences by silently replacing files.

## One synthetic original-source cross-cut scenario

1. Existing Stage28 source A/B owners and original WAL files created through its existing test fixture. A's original Intent/Skill/ActionSupervisor receives a **synthetic terminal Action** with a typed original Stage27 SkillInvocation/TargetContract; B unchanged.
2. Populate a **synthetic** `MOVE_PLACE` canonical journal row in A's original WAL using the source module's internal `_commit` validator + fsynced CAS. This is a **test-only fixture**, deliberately **bypassing a real native issuer**. It does NOT prove Action physical causality, even when the original validator accepts it.
3. Reopen with original Stage27 `PhysicalActionJournal.restore`, validate exact original WAL SHA, session, Intent/Skill/Action, Invocation/Preset/Target contract, native before/after probes; build a C1 episode using `assemble_stage27_c1_from_canonical_wal`. No input Memory is fabricated by the C test.
4. Original A Memory Owner explicitly adopts C1 via existing `retain_memory`. Existing Stage28 `capture_retired_resident_typed_world` saves the SAME A/B+World COMMITTED generation (all three synthetic dimensions, no World-only).
5. Existing Stage28 inert fork / execution copy / fresh native+Paper synthetic link / `Stage28FreshL1Eligibility` / new A native probe. The C `verify_c1_across_stage28_typed_epoch` readback checks the exact restored C1. The **original schema-v2 WAL digest and row bytes** must also agree between source COMMITTED cut and restored execution-copy.
6. Adversarial cases refuse altered source WAL, foreign bound Preset/Invocation, and incorrect WAL digest.

## Evidence limits and final intended real gate

**Only original code-path compatibility is tested**: simulated Mineflayer and Paper, an intentionally constructed terminal physical WAL, simulated owner choice and C2 hints, no real Gemma selection, no live Stage27 issuer/STOP settlement, no new physical authority. A SHA-valid WAL does not authenticate its real-world origin; the issuer's original physical event log and independently observed Paper data are required for such a claim.

Next real-world qualification must retrieve **the same operator-owned World UUID** from original Stage27 exact terminal WAL/native process and Stage28 COMMITTED full A/B world cut, then prove new-session native/Paper links and bounded L1 decisions. Never infer actual learning improvement from C3 context presence.

**Classification:** DEV_SYNTHETIC_SOURCE_SCHEMA_V2_CROSS_BRANCH_CHECK / REAL_WORLD_C1_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN.

## Independent C1-to-original WAL and Skill lineage admission

The C-specific `verify_stage27_wal_c1_across_stage28_typed_epoch` read-only verifier now checks that C1's claimed source WAL digest+Action IDs are **exactly** the canonical Stage27 source journal in the very same Stage28 A/B typed COMMITTED cut. It also checks original terminal child SkillExecution and committed Intent in SelfOwnerCut, original native session, target/preset/action links and byte-identical restored WAL. Its `C1Stage27SourceLineageWitness` explicitly disclaims real physical-effect attestation. A formally correct Memory with forged WAL provenance or wrong Action/Skill/Preset is held, even though it survived the Checkpoint itself.

It calls the original Stage27 journal's pure internal canonical `_read` (checks v2 grammar/checksum) rather than `PhysicalActionJournal.restore` on the immutable COMMITTED archive: the latter can create a sibling `.lock` file, making an otherwise read-only verification mutate the archived directory. Tests enforce archive file inventory unchanged.
