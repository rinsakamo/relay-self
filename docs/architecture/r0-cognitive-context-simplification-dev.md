# R0 architecture/compatibility audit — Current Schema Only + Recent3SelfView

**Lane:** R / Issue #1117 · **Design:** #828 / #833 §15 and subsequent sleep-epoch/Recent updates · **Owner integration:** #1047 / #1061 · **Independent audit:** #1088.

**Classification:** DEV_ONLY / CPU-OFFLINE CONTRACT / R1_HOLD / R2_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN. No World, Gemma, physical action or replay of past real-world evidence is claimed.

## Repository-first dependency pin

The repository's `main` on 2026-11-22 is `4348a614900c1d0828581a8eec2c523ba5ae237f` (2026-10-09). It lacks the modern original-owner integration. R0 is therefore **stacked on the unmerged B #1050** at starting commit `6e4e17909c6c2e1db5c1759ccf9c0cd000a1a5f4`. This dependency is not a merge or qualification of B, I, C or E. The R branch does not write to any lane's development branch.

For context, investigated diverging Drafts: #834 (old 3Self), #1050 (B original owner), #1076/#1080 (I), #1108 (C), #1109 (E) and #1089 (Q). Each has its own changing HEAD and evidence boundary; no cross-branch CI counts are combined into a proof.

## Actual ownership / projection graph

| Concrete location | Role (source, mutation, projection, persistence, interpretation, execution) | Risk and R0 decision |
| --- | --- | --- |
| `bd1b_owner_source_dev.BD1bOwnerSource` / `build_bd1b_owner_source` | **Source qualifier**: original Paper owned-log digest, native probe/session, resident/World epoch, A/B actor/source equality; under existing resident lock plus external Paper log reread | Reuse exactly; not independent native/Paper trust proof. A changed source/epoch makes a captured context unusable |
| `checkpointed_cognitive_runtime_dev.CheckpointedCognitiveOwner` | **Canonical mutable Self**: `retained`, `intent`, `pattern_registry`, `skills`, current WB observation, pending Questions, WAL-related owner paths | **Keep** the owner, its cohort/mutation gate and checkpoint format. Do not copy these fields into Context ownership |
| `resident_cognitive_work_owner_dev.ResidentCognitiveWorkOwner` | **Lifecycle/mutation gate**: per-Self online epoch, CPU tasks, `lock`, logout/quarantine, `_present_schemas` boot registration, original Owner API | A separate *responsibility*, not a second authoritative Self. Its ephemeral schema registration must match the Owner's current pattern revision. No automatic replay across reJOIN |
| `persistent_cognition.PersistentCognition` / `Memory` | **Canonical structured persistence**: identity/SOUL, accepted memory, appraisal, optional persisted pattern registry, continuity | No new DB. Memory has no individual revision/applicability/counterexample fields: R0 digest pointers, `applicability=UNKNOWN`, never an unconditional executable fact |
| `cognitive_minimal_dev.PatternRegistry` / `cpu_schema_epoch` / `assemble_l1_select` | **Owner active schema/preset revision and legacy L1 option preparation** | The optional persisted registry, active Owner registry, and Resident schema snapshot are three *representations* with different lifetimes, not three authoritative stores; must fence divergent revisions |
| `innate_schema.SchemaSnapshot` / `CognitiveSignal` / `signal_is_current` | **Read-only schema activation and semantic source-qualified output** | Reuse eligibility/revision checks. A Signal's `Provenance` string is not producer authentication. Missing signals/coverage stay UNKNOWN |
| `three_self_present.ThreeSelfProjection` / `LensClaim` / `PresentFrame.three_self` | **Legacy epistemic view** with OBSERVED native Body and coverage inference reprojected via 3Self, then Schema signals to Present | **Duplicated current path under #833 §15**: old `Native → LensClaim → Present` alongside target `Native → Schema → CURRENT`. Retain old path untouched; never make it a prerequisite of new CURRENT |
| `bd1b_owner_present_dev.build_bd1b_owner_present` | **Legacy ephemeral present**: source→Body OBSERVED claim, coverage inferred claim, `project_three_self`, `project_present_frame`, exploration signal, reread | The same source and Schema used to create R0 CURRENT, but legacy current native lens claims must not be copied into the new CURRENT |
| `owned_resident_physical_bridge_dev.OwnedResidentPhysicalBridge` | **Runtime / physical lifecycle**: original native/Paper path, resident Owner and observed source, GPU lane attachment, quarantine | Never introduce a second native dispatcher, physical ActionPort or GPU scheduler; R0 imports no action-issuer functions |
| `common_io.CognitiveTask` / `CognitionResultReceipt` / `result_is_current` | **Cognitive request and result generation/source admission** | Reuse negative controls for stale generation, deadline, unresolved, cancelled L2. It is *not* the original Owner's authenticated adopt receipt |
| Stage28b/Schema3 `self_owner_checkpoint_dev`, `bd1b_schema3_*_dev` | **Typed original persistent cut and inert restore**: Self, checkpoint generation, original Pattern/Question and WAL boundary | Immutable compatibility obligation; R0 adds no checkpoint keys, WAL commands, format changes or restore hooks |
| I2 #1080 (incl. `i_lane_i2d_self_schema_adoption_dev`) | **Experimental L2→L1 candidate/Schema acceptance** on divergent integration branch | Do not interpret hypothetical L2 output, old generation, or a self-consistent hash as a qualified current Schema installation |
| C #1108 `c_lane_retention_reuse_dev` / learning adapter | **Historical C1 experience and conditional C3 retrieval** from divergent branch | Reference-only retrieval at R0; C1/C3-specific applicability, counterexamples and authorized C2 acceptance require integrated B/I API and tests |
| E #1109 passive SENSE | **Perception and terrain/coverage capture, not owner** on divergent branch | Not incorporated in R0. No direct raw SENSE→CURRENT or claim of complete World coverage |

### Concrete duplication / deletion risk

1. **Two live-current semantic pipelines**: `BD1bOwnerPresent.present.three_self` still carries OBSERVED native-worldbody; the target normal L1/L2 CURRENT must instead carry only eligible Schema signals. Deleting the old view now would break B/I consumers, so R0 adds `read_original_owner_current` without any `project_three_self` or `project_present_frame` call.
2. **Registry three-way snapshots**: `retained.pattern_registry` may be persisted; `CheckpointedCognitiveOwner.pattern_registry` is the mutable canonical in-run authority; `ResidentCognitiveWorkOwner._present_schemas` is boot-time config. They require explicit owner revision equality and stale rechecks rather than unconditional consolidation.
3. **Duplicate L1 semantic material**: `assemble_l1_select` uses bounded SchemaFrame; legacy `PresentFrame` can separately include native lens claims. Copying both into a new prompt would duplicate and possibly contradict source/coverage. R0 builds no prompts and collects no token metrics.
4. **Memory versus perception versus RECENT**: `PersistentCognition.memories` are accepted past facts/interpretations, whereas `LensClaim` can carry hypotheses and `BD1bOwnerPresent` holds a current probe. Repeated RECENT must never synthesize C1/C2 accepted Memory; pointers carry digest and explicit `REMEMBERED`/applicability UNKNOWN.
5. **ReJOIN lifetime mismatch**: `ResidentCognitiveWorkOwner.current_scope` changes resident epoch/session on rebind; `_present_schemas` is run config, not restore proof. Old CURRENT and RECENT owner epoch are fenced on recheck; recent historical episodes may be retained later as history only, never automatically observed now.

## R0 implementation contract

Module: `src/relay_self/r0_cognitive_context_dev.py`.

- **CURRENT — `CurrentSchemaFrame`**: one original `BD1bOwnerSource` scope/epoch, current `SchemaSnapshot` and eligible `CognitiveSignal` tuple; the owner holds the actual observation. No new WorldModel, raw native object, `ThreeSelfProjection`, mutable gradient, full-coverage inference or default false for missing Schema. Existing signal epistemics are `HYPOTHETICAL/INFERRED/UNKNOWN`. Current `coverage` is UNKNOWN in R0, even if a bounded coverage evidence reference exists in the old Present.
- **RECENT — `RecentCognitionEntry` / `Recent3SelfView`**: an optional, single-Self, epoch-bound bounded view of subjective `LensClaim` references, disallowing `OBSERVED`. Partial lenses permitted. `recent_result_eligible` checks a typed common-IO result for L1/L2, ticket pairing, source, deadline and generation; it **never appends**. A matched *caller-provided* ticket is not an authenticated Original Owner adoption receipt. R0 does not claim to implement accepted `RecentEpisodeBuffer`, sleep compaction, or terminal C1/C2 write.
- **RETRIEVED — `RetrievedMemoryBundle` / `RetrievedMemoryRef`**: optional digest-pinned reference to exactly selected existing `PersistentCognition.Memory` under B's lock. Empty retrieval is normal. No copied content, new DB, index authority, auto C2 admission, inferred applicability, or ignored counterexample claims. Conditional suitability remains UNKNOWN until owner-integrated C3 evidence supports it.
- **`CognitiveContext`**: frozen assembly of CURRENT + optional RECENT/RETRIEVED; no Goal/Intent/Memory/Schema/Action/GPU/physical methods. `context_is_live` rechecks original native/Paper, resident epoch, registry snapshot and selected Memory digest immediately before use. External Paper can advance after return, so a subsequent consumer must recheck, not cache authorization.

**Important security limit:** The dataclasses and synthetic `Provenance` values alone can be constructed by untrusted callers; only the original producer/lifecycle bridge is an admissible live source. R0 is an OFFLINE context adapter, not a cryptographic proof of native origin or a new result acceptance service.

## Validation obligations / negative controls

`tests/test_r0_cognitive_context_dev.py` exercises both A/B owner readouts, unchanged legacy Present, the read-only byte hashes of original Self files, source and Schema revisions, foreign scopes, empty/duplicate/unsupported signals, no raw World bypass, incomplete coverage UNKNOWN, selective lens RECENT, old epoch and logout fences, L1 result cancellation/timeout/partial/old generation/wrong ticket/choice/foreign scope, L2 preemption and late result rejection, original Memory digests and invalidated references, unmatched/unadopted Memory, and absence of authority methods.

Existing suite obligations: `test_three_self_present_v01.py`, `test_bd1b_*_dev.py`, Stage28/Schema3 and original B restore/reJOIN tests; full pytest, Ruff, repository contracts, Mineflayer adapter, Paper witness. Different branch tests require integration before they can be claimed as tested at R0 HEAD.

## Stage gate (strict HOLD)

| Stage | Gate |
| --- | --- |
| R0 | Contract + focused/hostile tests + exact R head CI. No runtime migration |
| R1 | **HOLD** pending B/I API convergence on one verified HEAD, Q source/Owner independent audit, exact-head CI, Schema3 restore, 2 Self/reJOIN, legacy Present, C1/C3/I2 tests, and no mutation methods. Only then read-only shadow comparisons of source, UNKNOWN, token/time/CPU |
| R2 | **HOLD** pending separately audited R1 shadow, B/I integration, source/epoch and L2 cancel tests, checkpoint/reJOIN equivalence, read-only World confirmation and rollback. Only R2 may retire old native→3Self normal CURRENT projection |

## Q audit handoff

Independently test whether R0 and old Present read exactly the same B original A/B source, whether a changed Paper log/native source/epoch makes CURRENT stale, whether RECENT/RETRIEVED masquerade as OBSERVED, whether selected Memory files/WAL/Intent remain untouched, whether L2 cancellation/old GPU ticket results cannot be retained, and whether adding read-only shadow execution would cause extra Actions. Reuse existing Q tools rather than importing Q code into R product.
