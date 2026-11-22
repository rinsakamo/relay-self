# P0-D Stage23b × Cognitive v0.1 — accepted Preset two-Self owner checkpoint bridge

**Status: OFFLINE SYNTHETIC DEV ONLY.** This implementation branch has two merge parents: P0-D Stage23b [#908](https://github.com/rinsakamo/relay-self/pull/908) and Cognitive Preset durable knowledge [#917](https://github.com/rinsakamo/relay-self/pull/917). P0-D's latest physical issuer/STOP/WAL code is retained; unrelated earlier cognitive motor experiments are intentionally excluded. Do not merge until review.

## Actual bridged owner behavior

`CheckpointedCognitiveOwner.accept_parameter_preset` is an explicit **owner API**; caller must already have the Self adoption decision. It uses the existing cohort mutation lock, freshness admission, Self ID, expected registry revision, exact SkillDefinition ABI and capability check, with receipt event ID and provenance. Publication atomically changes the in-memory owner PatternRegistry and retained PersistentCognition v3 revision. It does **not** grant an Action. The accepted Skill's physical issuer remains separately fenced and unqualified to execute a parameterized Invocation.

P0-D `CognitionOwnerCohort.freeze` holds the existing external physical admission and validates that the original ActionSupervisor/WAL are clear. It builds one `SelfOwnerCut` under the same mutation lock and synchronizes the *same PatternRegistry revision* to the retained cognition snapshot. The existing per-Self exclusive `owner-state.json` fsync is followed by atomic `cognition.json` save/readback and a single coarse generation capture. If either durable file fails to save or cross-check, generation **does not gain COMMITTED marker** and hold applies; no action retry.

`SelfOwnerCut` writes **schema2 whenever accepted Presets are nonempty**, serializing the full strict typed `preset_registry_checkpoint.py` registry codec (Self identity, accepted receipts, Preset hashes, all Pattern/Skill/Cost/Constraints/Budget fields). Historical schema1 cuts with no accepted Presets remain readable and cannot pretend to contain adopted Presets. The previous `{revision,patterns}` projection is never used for live accepted parameters.

`capture_typed_generation`'s existing precommit validator now cross-checks copied `cognition.json` and `owner-state.json` for every Self in the exact roster. `verify_typed_generation`, `prepare_typed_owner_restore` and `staged_recover_cognition_cohort` revalidate both via the original committed generation/world/branch/roster, the physical WAL, accepted Preset hash/source and revision. Inconsistent or missing/cross-Self records, including legacy downgrade hiding a learned Preset, refuse. Existing v1 cognition and old v1 owner cuts without learned Presets remain subject to the legacy inert recovery contract.

## Two-Self restore exercise

Using the actual P0-D `RuntimeFixture` with two mutable original `CheckpointedCognitiveOwner` instances, synthetic World files and controlled external physical/rejoin callbacks:

1. Self A and B each adopt a named EAT Preset via their **own** owner mutation lock; learned receipt and revision stay scoped to the adopting Self.
2. The existing original `CoordinatedAutosaveRuntime` freezes the two owners; a **single** P0-D generation commits both cognition and owner-state files, preserves per-Self WAL and strict owner identity/peer checks.
3. Subsequent memories from the old epoch do not leak into the committed generation. The World is restored to a **new branch** using the existing verified restore function, yielding inert Self owners with `native_session_bound=False`, `issue_authorized=False`, `old_skill_resume_authorized=False`.
4. A fresh **synthetic** WorldBody Percept is constructed with a new session and inventory Target for each Self. CPU `cpu_schema_epoch(...use_registered_presets=True)` yields fully bound `SkillInvocation` choices; the existing `RelayEngine` scripted bounded choice returns only a numeric choice. Fresh-probe `resolve_l1_choice` succeeds without any physical native Action, while the restored WAL remains clear.

Negative controls verify that an accepted Preset present in the owner cut but missing in cognition, or present in cognition but downgraded out of the owner cut, prevents a complete generation; owner adoption during checkpoint fence is refused; old physical issuer permissions never arise from the recovered knowledge.

## Important limitations

- **No actual Paper or Mineflayer World** was started, no Gemma/GPU call, no native EAT/ATTACK/MOVE Action and no actual 60s timing attestation. The World/rejoin are source-shaped synthetic fixtures, not proof of live multi-Self reintegration.
- The historical original unresolved physical MOVE WAL was not reissued, changed or marked resolved. P0-D STOP/settling owner remains authoritative; parameterized physical ActionPort budget/constraints admission is **HOLD**.
- The Self-acceptance receipt remains externally provided by the owner API: these tests establish owner mutation and durability, not autonomous L2 proposal evaluation or actual long-run learning advantage.
- The separate per-Self resident Work/GPU owners and real concurrent multi-Self living World qualification remain distinct. The test uses the existing *global cohort* owner for two Self; never attach two ownership facades to one live mutable Self.
- This is finite offline qualification: **`TWO_SELF_PRESET_DUAL_CUT_OFFLINE_DEV_PASS`** only when exact-head CI green; **`REAL_WORLD_AUTOSAVE_NOT_ATTESTED / PHYSICAL_PARAMETRIC_ISSUE_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`**.

## Next verification

On a newly isolated Paper 1.21.8 World, under the existing user-approved EULA/real World DEV conditions, validate a *newly adopted* Preset survives an actual STOP/clean WAL, saved World+2 Self generation, process restart/rejoin, fresh native Target probe and a read-only L1 selection. Require old LLM output and Action leases to be invalidated, and do not issue parameterized physical actions until separate issuer acceptance tests succeed.
