# Cognitive v0.1 — accepted Skill Preset durability at Self checkpoint

**Status: OFFLINE DEV / DATACUT ROUNDTRIP ONLY / REAL P0-D OWNER-CUT V2 BRIDGE OPEN.**

Related: #828 #829 #843, stacked Draft #917 → #915 → #912 → #882, and independent P0-D #860 staged checkpoint owner.

## What is persisted

The existing `PersistentCognition` snapshot (identity, memories, appraisal dispositions) is now **schema v3**, adding optional `pattern_registry` as immutable typed Self-owned cognitive knowledge. Existing `save_persistent_cognition` still writes a temporary JSON, fsyncs the temporary file, and atomically renames into the existing Self cognition path. This is the **same cognition file** that #860 `capture_generation` copies and checksums, rather than a new independently owned memory database.

Its nested registry uses **codec schema v2** with: Self ID, registry revision, complete versioned SchemaPatterns, bound accepted Presets, target-safe typed arguments, Goal+Skill Definition digest, expected costs, Constraints, Budget, owner-provided acceptance event IDs/provenances, each `preset_ref`, and a canonical full `registry_ref` digest. This digest detects inconsistent or edited Pattern text even if Preset bytes are unchanged. It is *not* an authenticity signature; committed generation SHA256 and actual Self owner privileges are independent.

Old cognition schema v1/v2 can still be loaded with `pattern_registry=None`. They do **not** imply that Presets were secretly reconstructed. New v3 with a malformed/foreign/partially missing registry refuses to load. Identity/Memory/SOUL behavior remains unchanged.

`PersistentCognition.retain_schema_registry(registry, expected_revision)` returns a new immutable cognition snapshot and rejects stale or rolled-back revisions. It does not itself decide Self acceptance and it does not write the file until the existing cognition owner commits with `save_persistent_cognition`. The earlier `accept_skill_parameter_preset` remains the pure Self-accepted CAS publisher; caller-supplied acceptance receipts must be independently authenticated by the real Self owner.

## P0-D typed Owner Cut bridge (not yet wired)

P0-D `SelfOwnerCut.pattern_registry` in the **separate #860 stack** currently serializes just `{revision, patterns}` under owner-cut schema1. It **does not carry** accepted Presets, so an old typed cut is NOT eligible to act as an equivalent restored v3 cognitive registry. Do **not** claim the two forms are automatically compatible or quietly downgrade a new registry to the old format.

After bringing #917 to the same code stack as #860, the P0-D owner-state writer/reader must:

1. Snapshot the Self's **same quiesced PatternRegistry revision** into both durable `PersistentCognition` v3 and typed owner-state field. Under the existing owner mutation lock and physical/WAL quiescence gate, call `encode_pattern_registry(registry, self_id=cut.self_id)`; update the `SelfOwnerCut` codec to schema2 for this field, and do not publish an old owner-cut schema1 for a registry with accepted Presets.
2. Verify the copied cognition JSON and typed owner cut belong to the **same generation, World/branch, roster, Self, and durable file inventory**. Only after the existing `verify_typed_generation` and World restore bundle hash checks, call `reconcile_restored_self_schema_file(..., owner_cut_pattern_registry=decoded_cut_field)`. It compares exact source-qualified Schema/accepted Preset/receipt digests and revision; missing/foreign/mismatch/legacy owner cut -> HOLD before any re-admission.
3. The result is an **`InertRestoredSchema`**: retained hypothesis/Pattern/Preset knowledge only, with `new_worldbody_observation_required=True`, `old_target_current=False`, `native_action_issue_authorized=False`, `old_intent_or_skill_resume_authorized=False`, `old_llm_output_current=False`. Do NOT restore L0 interpreter cursors, native controls, issue leases, old L1 options, in-flight Action, stale GPU outputs or peer deliveries.
4. Once the new Paper World and native Self are independently rejoined and current Perception is established, run a **new** Schema epoch and rebuild fresh complete SkillInvocations. Historical Preset/TargetContract source may still be invalid for the new World branch, so reject it instead of laundering it into a new live target. Real ActionPort budget/constraint admission remains a separate owner and remains HOLD in this PR.

The v3 cognition save/load and deterministic reconciliation helper are **implemented** on this stack, including file-based tests. The concrete P0-D `SelfOwnerCut` schema2 writer and its atomic two-file owner quiescence/recovery join are **not implemented here** because that module is on the independent #860 stack. No actual coordinated World+Self generation was captured or restored on #917.

## Negative controls

- Unknown fields, missing arrays, bad registry full digest, altered Goal/Skill mapping, forged/bad individual Preset revision, cross-Self receipt/identity, unbounded typed budget, invalid position and typed TargetContract, CAS rollback or stale owner revision all refuse.
- Original v1/v2 loads safely with no accepted Preset; it cannot satisfy the new full-Owner-Cut reconciliation without an explicit migration.
- Independent cognition+Owner Cut tamper/mismatch never reaches `InertRestoredSchema`.
- Correct independently encoded owner-state and persisted cognition can be reconciled as inert knowledge. Inert flags disallow physical issue/replay even when the *cognitive* registry matches.
- No real Minecraft/Paper/Gemma, actual GPU operation, full multi-Self checkpoint, rollback, Authenticated Self owner adoption, QUAL or SCIENCE evidence is claimed.

**Classification:** `PERSISTENT_PRESET_COGNITION_V3_OFFLINE_DEV_PASS` only after exact-head CI, `P0D_OWNER_CUT_V2_BRIDGE_PENDING / PHYSICAL_ISSUE_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
