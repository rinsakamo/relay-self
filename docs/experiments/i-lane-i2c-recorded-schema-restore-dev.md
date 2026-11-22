# I Lane I2c — original recorded Schema in a future typed generation (CPU/offline DEV)

Issue #1078; I2 Draft PR #1080; I1 independent Paper/Native audit #1061; original B Owner #1050. This is **NOT** a migration of past Stage28b generations and not a real World/Gemma claim.

## The gap

Previously the actual Stage28b typed `owner-state.json` persisted the original PatternRegistry, Intent, Skill and Question refs, but did **not** persist the original resident `SchemaSnapshot` activation state. Registry membership never implies Schema FULL. The existing Stage28c2a restored A/B from the original same-generation cut, so no legitimate API could re-create a missing recorded activation. For I1's historical A/B (four innate hunger/defense/fatigue/oxygen patterns, no exploration Pattern), the only valid result stays NO_QUALIFIED_EXPLORATION_GOAL.

## New *future-only* recording and explicit restoration

- `ResidentCognitiveWorkOwner.recorded_retired_schema` reads an already registered per-Self snapshot only after the **original** resident is fully retired and the original registry has not changed. It returns absence, not a bootstrap guess, for an unregistered Self.
- At the existing Stage28b **new** typed cut boundary, `_retired_owner_snapshots` records such a snapshot only when supplied by this original retired resident and when the same owner PatternRegistry has also been durably saved in its own `cognition.json`. It binds the exact cognition byte SHA-256 and the exact snapshot to the owner cut in `owner-state.json`. It never changes or reconstructs earlier committed generations.
- `SelfOwnerCut` now supports optional `recorded_schema`. Schema v1 and v2 encodings remain byte/field compatible; only a newly recorded activation selects owner cut schema **v3** (which requires an exact cognition digest). The v3 codec decodes strictly bounded typed specs/modes/provenance/dependencies, compares canonical bytes, Self identity and Registry revision, and is covered by the **same committed typed-generation file manifest**, not an unbound sidecar. The SHA is an integrity/source-currentness check, not an independent signature of a Self decision.
- `bootstrap_original_recorded_a_b_schemas` is an **explicit OFFLINE** adapter after the unchanged pinned `prepare_recovered_a_b_resident_owners`. It re-verifies the original complete typed generation and the already pinned COMMITTED SHA, every original and restored cognition/owner/WAL file, both original A/B typed cuts, exact restored owner/Registry, and cold per-Self resident scopes.
- Only if **both A and B** have attested v3 records does the adapter call the existing original `ResidentCognitiveWorkOwner.register_present_schema`. That API performs the original strict exploration Pattern v1 / module FULL qualification and never installs a new Pattern or grants a Skill. If either registration fails, it rolls back both transient registrations under the single original resident lock. It creates no new owner or scheduler. On successful CPU readback, the restored owners still require a new Native JOIN/WorldBody; physical Action remains denied.

## Adversarial regression

`tests/test_i_lane_i2c_recorded_schema_restore_dev.py` covers: two-Self future typed snapshot roundtrip, exact saved FULL vs missing/partial/older snapshots, CPU retirement prior to cut, committed SHA mismatch, damaged owner/cognition/WAL, changed original Registry/owner mode and duplicate registration, foreign Self, old revision, unsupported module mode, malformed provenance and noncanonical Schema encoding. All local synthetic World files are artificial fixtures, not Minecraft.

The I2b read-only shared L1 contract, previous I1 source audit files and all parallel lane evidence remain unchanged. **No real GPU, GGUF, Paper, Native process, World, L2 or physical Action was executed in I2c.**

## Remaining authority gaps

- **Historic restored Schema HOLD remains:** old schema1/2 and I1's old actual Stage28b W100 cut have no recorded Schema activation. They cannot become FULL by code/config replay. This work qualifies a **new future generation format**, not an attestation that existing World evidence contained the activation.
- The original `register_present_schema` confirms an explicit configuration and an eligible Pattern, but does not by itself attest a Self-generated cognitive acceptance of a learned module. A learned exploration Pattern still needs an original source-qualified Self acceptance/Owner transaction and re-cut. The verified generated v3 digest is not an independent proof of an earlier Self decision.
- The new v3 path has CPU/offline synthetic tests only. Any actual original Owner/Native/Paper/Gemma flow needs a new isolated World, with strict real preflight and at most one controlled DEV trial, plus independent source/evidence audit. Do not reuse the old Stage28b or I1 Paper trace as a new I2c result.
- Live GPU `/slots` and HTTP request/response exact bytes, D Question ADOPT, Goal/Intent lifecycles, persistent checkpoint over live reJOIN and C learning remain separate gates. Existing `QUAL_NO_GO` and `SCIENCE_NOT_RUN` still apply. No Draft PR merge.

Scoped classification once a new exact-HEAD 5/5 CI completes: `I2C_FUTURE_RECORDED_SCHEMA_CUT_RESTORE_CPU_OFFLINE_DEV_PASS`. Do **not** use `I2B_GENERAL_RESTORED_SCHEMA_PASS`; existing historical cuts remain `I2C_HISTORIC_SCHEMA_ACTIVATION_HOLD`.
